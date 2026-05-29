from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import Request

from quantagent.api.config.settings import _SOURCE_REPO_ROOT
from quantagent.core.registry import PluginRegistry, build_plugin_registry


_REPO_ROOT = Path.cwd()


def get_plugin_registry(request: Request) -> PluginRegistry:
    """从 app.state 取 Registry，不存在时按当前运行目录创建一个。"""
    registry = getattr(request.app.state, "plugin_registry", None)
    if registry is None:
        settings = request.app.state.settings
        repo_root = find_repo_root()
        runtime_dir = Path(settings.RUNTIME_DIR)
        if not runtime_dir.is_absolute():
            runtime_dir = repo_root / runtime_dir
        registry = build_plugin_registry(
            official_root=repo_root / "plugins",
            runtime_root=runtime_dir / "plugins",
        )
        # Registry 挂在 app.state 上，后续请求复用同一个扫描视图；rescan action 显式刷新。
        request.app.state.plugin_registry = registry
    return registry


@lru_cache(maxsize=1)
def find_repo_root() -> Path:
    """定位 QuantAgent 仓库根, 避免把 apps/api/runtime 误判成项目根。"""
    candidates: list[Path] = []
    if _SOURCE_REPO_ROOT is not None:
        candidates.append(_SOURCE_REPO_ROOT)
    candidates.extend([Path.cwd(), *Path(__file__).resolve().parents])
    for candidate in candidates:
        if _is_repo_root_candidate(candidate):
            return candidate
    return _REPO_ROOT


def _is_repo_root_candidate(candidate: Path) -> bool:
    return (
        (candidate / "pyproject.toml").is_file()
        and (candidate / "apps" / "api").is_dir()
        and (candidate / "plugins").is_dir()
    )
