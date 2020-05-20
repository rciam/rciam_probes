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

class LoggingDefaults(Enum):
    LOG_FILE = "../var/logs/rciam_probes.log" # Path relative to root of the project
    LOG_FORMATTER = "%(asctime)s %(processName)s[%(process)d]: %(levelname)s: %(filename)s[%(funcName)s] - %(message)s"