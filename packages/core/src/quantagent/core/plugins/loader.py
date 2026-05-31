from __future__ import annotations

import importlib
import importlib.util
import importlib.machinery
from pathlib import Path
import sys
import threading
import types

from quantagent.core.registry.models import PluginRecord, PluginStatus


_PLUGIN_LOAD_LOCK = threading.RLock()


class PluginEntrypointLoadError(RuntimeError):
    """Raised when a plugin entrypoint cannot be imported safely."""


def load_plugin_entrypoint(record: PluginRecord) -> object:
    if record.status != PluginStatus.VALID or record.manifest is None:
        raise PluginEntrypointLoadError("Plugin record is not loadable.")

    module_name, separator, attribute_name = record.manifest.entrypoint.partition(":")
    if not separator or not module_name.strip() or not attribute_name.strip():
        raise PluginEntrypointLoadError("Plugin entrypoint must use module:attribute syntax.")

    plugin_dir = record.path.resolve()
    module_path = _find_plugin_module_file(module_name.strip(), plugin_dir=plugin_dir)
    if module_path is None:
        raise PluginEntrypointLoadError("Plugin entrypoint module file was not found.")

    plugin_root_name = f"quantagent_plugin_{record.id.replace('.', '_')}"
    target_module_name = f"{plugin_root_name}.{module_name.strip()}"
    try:
        # 插件加载会临时改写 import 视图；用全局锁串行化，避免并发请求互相污染 sys.modules/sys.path。
        with _PLUGIN_LOAD_LOCK:
            with _plugin_import_root(plugin_dir, plugin_root_name):
                _purge_plugin_modules(plugin_root_name)
                _ensure_plugin_root_package(plugin_root_name, plugin_dir)
                module = importlib.import_module(target_module_name)
    except Exception as exc:  # pragma: no cover - defensive import boundary
        raise PluginEntrypointLoadError("Plugin entrypoint import failed.") from exc

    if not hasattr(module, attribute_name.strip()):
        raise PluginEntrypointLoadError("Plugin entrypoint attribute was not found.")
    return getattr(module, attribute_name.strip())


def _find_plugin_module_file(module_name: str, *, plugin_dir: Path) -> Path | None:
    module_parts = module_name.split(".")
    if not module_parts or any(not part or part == ".." for part in module_parts):
        return None

    module_root = plugin_dir.joinpath(*module_parts)
    candidates = (module_root.with_suffix(".py"), module_root / "__init__.py")
    for candidate in candidates:
        if candidate.is_file() and _is_path_inside_root(candidate, plugin_dir):
            return candidate
    return None


def _is_path_inside_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _ensure_plugin_root_package(plugin_root_name: str, plugin_dir: Path) -> None:
    package = types.ModuleType(plugin_root_name)
    package.__file__ = str(plugin_dir)
    package.__package__ = plugin_root_name
    package.__path__ = [str(plugin_dir)]  # type: ignore[attr-defined]
    package.__spec__ = importlib.machinery.ModuleSpec(plugin_root_name, loader=None, is_package=True)
    sys.modules[plugin_root_name] = package


def _purge_plugin_modules(plugin_root_name: str) -> None:
    for module_name in tuple(sys.modules):
        if module_name == plugin_root_name or module_name.startswith(f"{plugin_root_name}."):
            sys.modules.pop(module_name, None)


class _plugin_import_root:
    """临时把插件根目录加入 import 搜索路径，允许 entrypoint 拆分同目录模块。"""

    def __init__(self, plugin_dir: Path, plugin_root_name: str) -> None:
        self.plugin_path = plugin_dir
        self.plugin_dir = str(plugin_dir)
        self.plugin_root_name = plugin_root_name
        self.inserted = False
        self.shadowed_modules: dict[str, object] = {}

    def __enter__(self) -> None:
        if self.plugin_dir not in sys.path:
            sys.path.insert(0, self.plugin_dir)
            self.inserted = True
        # 插件常用 helper/config 等短模块名；加载前临时隔离同名模块，避免不同插件互相串用。
        for module_name in _top_level_module_names(self.plugin_path):
            loaded_module = sys.modules.get(module_name)
            if loaded_module is not None:
                self.shadowed_modules[module_name] = loaded_module
                sys.modules.pop(module_name, None)

    def __exit__(self, _exc_type, _exc, _tb) -> None:
        for module_name in _top_level_module_names(self.plugin_path):
            sys.modules.pop(module_name, None)
        _purge_plugin_modules(self.plugin_root_name)
        sys.modules.update(self.shadowed_modules)
        if self.inserted:
            try:
                sys.path.remove(self.plugin_dir)
            except ValueError:
                return None
        return None


def _top_level_module_names(plugin_dir: Path) -> set[str]:
    module_names: set[str] = set()
    for child in plugin_dir.iterdir():
        if child.name.startswith("__"):
            continue
        if child.is_file() and child.suffix == ".py":
            module_names.add(child.stem)
        elif child.is_dir() and (child / "__init__.py").is_file():
            module_names.add(child.name)
    return module_names
