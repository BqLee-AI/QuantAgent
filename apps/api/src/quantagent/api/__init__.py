from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import tomllib


def _read_version() -> str:
    """Resolve the package version from installed metadata or local pyproject."""
    try:
        return version("quantagent_api")
    except PackageNotFoundError:
        pyproject_path = Path(__file__).resolve().parents[3] / "pyproject.toml"
        with pyproject_path.open("rb") as pyproject_file:
            pyproject_data = tomllib.load(pyproject_file)
        return pyproject_data["project"]["version"]


__all__ = ["__version__"]

__version__ = _read_version()
