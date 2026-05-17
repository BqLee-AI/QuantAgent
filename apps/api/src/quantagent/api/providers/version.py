from quantagent.api import __version__
from quantagent.api.schemas.system import VersionResponse


def get_version_info() -> VersionResponse:
    """Return static API metadata as a replaceable provider seam."""
    return VersionResponse(service="quantagent-api", api_version="v1", version=__version__)
