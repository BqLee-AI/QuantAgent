from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

from quantagent.core.registry.models import PluginRecord, PluginStatus


class PluginEntrypointLoadError(RuntimeError):
    """Raised when a plugin entrypoint cannot be imported safely."""


def load_plugin_entrypoint(record: PluginRecord) -> object:
    if record.status != PluginStatus.VALID or record.manifest is None:
        raise PluginEntrypointLoadError("Plugin record is not loadable.")

    module_name, separator, attribute_name = record.manifest.entrypoint.partition(":")
    if not separator or not module_name.strip() or not attribute_name.strip():
        raise PluginEntrypointLoadError("Plugin entrypoint must use module:attribute syntax.")

    plugin_dir = record.path.resolve()
    module_path = plugin_dir.joinpath(*module_name.strip().split(".")).with_suffix(".py")
    if not module_path.is_file():
        raise PluginEntrypointLoadError("Plugin entrypoint module file was not found.")

    spec_name = f"quantagent_plugin_{record.id.replace('.', '_')}"
    spec = importlib.util.spec_from_file_location(spec_name, module_path)
    if spec is None or spec.loader is None:
        raise PluginEntrypointLoadError("Plugin entrypoint module could not be loaded.")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # pragma: no cover - defensive import boundary
        raise PluginEntrypointLoadError("Plugin entrypoint import failed.") from exc

    if not hasattr(module, attribute_name.strip()):
        raise PluginEntrypointLoadError("Plugin entrypoint attribute was not found.")
    return getattr(module, attribute_name.strip())
