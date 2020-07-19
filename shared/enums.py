from enum import Enum
from pathlib import Path


class NagiosStatusCode(Enum):
    OK = 0
    WARNING = 1
    CRITICAL = 2
    UNKNOWN = 3

class LoggingLevel(Enum):
    debug = 10
    info = 20
    warning = 30
    error = 40
    critical = 50

class EGIDefaults(Enum):
    ServiceAccountIdp = "https://login.ics.muni.cz/idp/shibboleth"
    EGISSOIdp = "https://www.egi.eu/idp/shibboleth"


class LoggingDefaults(Enum):
    LOG_FILE = str(Path(__file__).parent.parent.joinpath("local").joinpath("log").joinpath("rciam_probes.log"))
    LOG_FORMATTER = "%(asctime)s %(processName)s[%(process)d]: %(levelname)s: %(filename)s[%(funcName)s] - %(message)s"


class AuthenticateTxt(Enum):
    Success = "Authentication Succeeded"
    Failed = "Authentication Failed"
    AlertFailed = "Authentication with Alert failed."
