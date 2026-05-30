from contextlib import asynccontextmanager
from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

from fastapi import FastAPI

from quantagent.api import __version__
from quantagent.api.config.settings import Settings, settings
from quantagent.api.db import initialize_database, shutdown_database
from quantagent.api.http.exceptions import register_exception_handlers
from quantagent.api.http.middleware import RequestContextMiddleware
from quantagent.api.observability.logging import configure_api_logging, shutdown_api_logging
from quantagent.api.routers.v1 import register_api_v1_routes

_DEV_SERVER_PID_DIR = Path("data/api/dev-server")
_DEV_SERVER_STOP_TIMEOUT_SECONDS = 2.0
_DEV_SERVER_STOP_POLL_INTERVAL_SECONDS = 0.1
_PID_ROLE_RELOADER = "reloader"
_PID_ROLE_WORKER = "worker"


@dataclass(frozen=True)
class DevServerStopSummary:
    terminated_pids: tuple[int, ...]
    stubborn_pids: tuple[int, ...]
    stale_pid_files: tuple[str, ...]


def _dev_server_pid_dir(current_settings: Settings) -> Path:
    return current_settings.RUNTIME_DIR / _DEV_SERVER_PID_DIR


def _dev_server_pid_path(current_settings: Settings, role: str) -> Path:
    return _dev_server_pid_dir(current_settings) / f"{role}.pid"


def _write_dev_server_pid(current_settings: Settings, role: str, pid: int) -> None:
    path = _dev_server_pid_path(current_settings, role)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{pid}\n", encoding="utf-8")


def _read_dev_server_pid(current_settings: Settings, role: str) -> int | None:
    path = _dev_server_pid_path(current_settings, role)
    if not path.is_file():
        return None
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _remove_dev_server_pid(current_settings: Settings, role: str, *, expected_pid: int | None = None) -> None:
    path = _dev_server_pid_path(current_settings, role)
    if not path.exists():
        return
    if expected_pid is not None:
        recorded_pid = _read_dev_server_pid(current_settings, role)
        if recorded_pid is not None and recorded_pid != expected_pid:
            return
    path.unlink(missing_ok=True)


def _pid_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return True
    return True


def _read_process_command(pid: int) -> str:
    proc_cmdline = Path("/proc") / str(pid) / "cmdline"
    if proc_cmdline.is_file():
        try:
            raw = proc_cmdline.read_bytes()
        except OSError:
            raw = b""
        if raw:
            return raw.replace(b"\x00", b" ").decode("utf-8", errors="ignore").strip()
    result = subprocess.run(
        ["ps", "-p", str(pid), "-o", "command="],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


def _looks_like_api_dev_process(command: str) -> bool:
    lowered = command.lower()
    return any(
        marker in lowered
        for marker in (
            "uv run api",
            "uvicorn",
            "watchfiles",
            "quantagent.api.main",
        )
    )


def _find_listener_pids(current_settings: Settings) -> set[int]:
    if shutil.which("lsof") is None:
        return set()
    result = subprocess.run(
        ["lsof", f"-iTCP:{current_settings.API_PORT}", "-sTCP:LISTEN", "-t"],
        capture_output=True,
        text=True,
        check=False,
    )
    pids: set[int] = set()
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            pid = int(stripped)
        except ValueError:
            continue
        if _looks_like_api_dev_process(_read_process_command(pid)):
            pids.add(pid)
    return pids


def _collect_dev_server_pids(current_settings: Settings) -> tuple[dict[str, int], set[int]]:
    registered: dict[str, int] = {}
    for role in (_PID_ROLE_RELOADER, _PID_ROLE_WORKER):
        if (pid := _read_dev_server_pid(current_settings, role)) is not None:
            registered[role] = pid
    fallback = _find_listener_pids(current_settings)
    return registered, fallback


def _terminate_processes(pids: set[int]) -> tuple[tuple[int, ...], tuple[int, ...]]:
    target_pids = {pid for pid in pids if _pid_exists(pid)}
    if not target_pids:
        return (), ()
    for pid in target_pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            continue
    deadline = time.monotonic() + _DEV_SERVER_STOP_TIMEOUT_SECONDS
    remaining = set(target_pids)
    while remaining and time.monotonic() < deadline:
        remaining = {pid for pid in remaining if _pid_exists(pid)}
        if remaining:
            time.sleep(_DEV_SERVER_STOP_POLL_INTERVAL_SECONDS)
    for pid in set(remaining):
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            remaining.discard(pid)
    if remaining:
        time.sleep(_DEV_SERVER_STOP_POLL_INTERVAL_SECONDS)
    remaining = {pid for pid in remaining if _pid_exists(pid)}
    terminated = tuple(sorted(target_pids - remaining))
    stubborn = tuple(sorted(remaining))
    return terminated, stubborn


def _cleanup_stale_dev_server_pid_files(current_settings: Settings) -> tuple[str, ...]:
    stale_roles: list[str] = []
    for role in (_PID_ROLE_RELOADER, _PID_ROLE_WORKER):
        pid = _read_dev_server_pid(current_settings, role)
        if pid is None or not _pid_exists(pid):
            _remove_dev_server_pid(current_settings, role)
            stale_roles.append(role)
    return tuple(stale_roles)


def _stop_dev_server(current_settings: Settings) -> DevServerStopSummary:
    registered, fallback = _collect_dev_server_pids(current_settings)
    target_pids = set(registered.values()) | fallback
    terminated, stubborn = _terminate_processes(target_pids)
    stale_pid_files = _cleanup_stale_dev_server_pid_files(current_settings)
    return DevServerStopSummary(
        terminated_pids=terminated,
        stubborn_pids=stubborn,
        stale_pid_files=stale_pid_files,
    )


def create_app(app_settings: Settings | None = None) -> FastAPI:
    """构建 FastAPI 应用，并注册公共中间件、异常处理和路由。"""
    current_settings = app_settings or settings

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # 将数据库初始化放在生命周期里，避免测试或脚本在创建应用时就提前建立连接。
        try:
            # reload 模式下 reloader 和 worker 是两个独立进程；记录 worker pid 供 api-stop 一次性回收残留进程。
            _write_dev_server_pid(current_settings, _PID_ROLE_WORKER, os.getpid())
            configure_api_logging(current_settings)
            initialize_database(app, current_settings)
            yield
        finally:
            shutdown_database(app)
            shutdown_api_logging()
            _remove_dev_server_pid(current_settings, _PID_ROLE_WORKER, expected_pid=os.getpid())

    app = FastAPI(title="QuantAgent API", version=__version__, lifespan=lifespan)
    app.state.settings = current_settings
    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)
    register_api_v1_routes(app, current_settings)
    return app


app = create_app()


def _should_enable_reload(current_settings: Settings) -> bool:
    """本地开发入口默认启用热更新，非本地环境保持单进程启动。"""
    return current_settings.APP_ENV.lower() in {"development", "local"}


def run() -> None:
    """使用配置中的主机和端口启动开发服务器。"""
    import uvicorn

    try:
        _write_dev_server_pid(settings, _PID_ROLE_RELOADER, os.getpid())
        uvicorn.run(
            "quantagent.api.main:app",
            host=settings.API_HOST,
            port=settings.API_PORT,
            reload=_should_enable_reload(settings),
        )
    finally:
        _remove_dev_server_pid(settings, _PID_ROLE_RELOADER, expected_pid=os.getpid())


def stop() -> None:
    """停止本地开发 API 残留进程，优先回收记录到 runtime 的 reloader/worker。"""
    summary = _stop_dev_server(settings)
    if summary.terminated_pids:
        print(f"Stopped API dev server pids: {', '.join(str(pid) for pid in summary.terminated_pids)}")
    else:
        print("No running API dev server pids found.")
    if summary.stubborn_pids:
        print(f"Processes still alive after SIGKILL: {', '.join(str(pid) for pid in summary.stubborn_pids)}")
    if summary.stale_pid_files:
        print(f"Cleaned stale pid files: {', '.join(summary.stale_pid_files)}")


def reset() -> None:
    """兼容本地开发口令，当前与 api-stop 等价。"""
    stop()
