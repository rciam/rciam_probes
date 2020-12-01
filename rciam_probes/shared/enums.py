from enum import Enum

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


class ParamDefaults(Enum):
    LOG_PATH = r"/var/log/rciam_probes/"
    LOG_FILE = r"/var/log/rciam_probes/rciam_probes.log"
    LOG_OWNER = "nagios"
    LOG_FORMATTER = "%(asctime)s %(processName)s[%(process)d]: %(levelname)s: %(filename)s[%(funcName)s] - %(message)s"
    FIREFOX_PATH = r"/usr/bin/firefox"
    JSON_PATH = r"/var/www/html"
    GECKODRIVER_PATH = r"/usr/include/rciam_probes/driver/geckodriver"


class AuthenticateTxt(Enum):
    Success = "Authentication Succeeded"
    Failed = "Authentication Failed"
    AlertFailed = "Authentication with Alert failed."
