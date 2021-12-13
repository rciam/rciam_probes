#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import sys
from json import JSONDecodeError

import pkg_resources
import requests
import xmltodict
import time as t
import hashlib
import json
import datetime

from shutil import chown
from pathlib import Path
from OpenSSL import crypto
from datetime import datetime, timezone
from time import mktime, time, gmtime
from urllib3.exceptions import NewConnectionError

from rciam_probes.shared.enums import ParamDefaults, LoggingLevel, NagiosStatusCode
import rciam_probes.shared.templates as tpl


def configure_logger(args):
    """
    Get the argument list from command line and configure the logger
    :param args: arguments retrieved from command line
    :type args: dict
    :return: Logger object
    :rtype Logger: Logger object
    """
    # Set the logfile
    if not args.log:
        args.log = ParamDefaults.LOG_FILE.value

    # Set the log verbosity, Defaults to error
    args.verbose = get_verbosity_level(args.verbose)

    # Create the Logger
    logger = logging.getLogger(__name__)
    logger.setLevel(args.verbose)

    if args.console:
        # Create the Handler for logging data to stdout
        logger_handler = logging.StreamHandler(sys.stdout)
    else:
        # Create the log file if not exists
        # First try in the /var/log/rciam_probes path. This is the path used when
        # installing with rpm. If the path is not available then create it under
        # current user home directory
        log_path = Path('/').joinpath('var').joinpath('log').joinpath('rciam_probes')
        if not log_path.is_dir():
            log_path = Path.home().joinpath('var').joinpath('log').joinpath('rciam_probes')
            log_path.mkdir(0o755, parents=True, exist_ok=True)

        log_file = log_path.joinpath('rciam_probes.log')
        log_file.touch(exist_ok=True)
        args.log = str(log_file)
        chown(args.log, user=args.logowner, group=args.logowner)
        # Create the Handler for logging data to a file
        logger_handler = logging.FileHandler(args.log)
    logger_handler.setLevel(args.verbose)

    # Create a Formatter for formatting the log messages
    logger_formatter = logging.Formatter(ParamDefaults.LOG_FORMATTER.value)
    # Add the Formatter to the Handler
    logger_handler.setFormatter(logger_formatter)
    # Add the Handler to the Logger
    logger.addHandler(logger_handler)

    return logger


def get_xml(url, timeout=5, logger=None):
    """
    Get and parse an xml available through a url
    :param url: URL
    :type url: string

    :return: Data parsed from the xml
    :rtype: dict

    :param value: logger object
    :type object

    :raises Exception: Exceptions might occurs from the URL format and get request. Or from xml parsing
    """
    try:
        requests.packages.urllib3.disable_warnings()
        response = requests.get(url, verify=False, timeout=timeout)
        parsed_response = xmltodict.parse(response.text)
    except NewConnectionError as nce:
        if logger is not None:
            logger.critical(nce.message)
        error_msg = "Http Connection failed."
        raise RuntimeError(error_msg)

    return parsed_response


def get_json(url, timeout=5, logger=None):
    """
    Get and parse a json file available through a url
    :param url: URL
    :type url: string

    :return: Data parsed from json
    :rtype: dict

    :param value: logger object
    :type object

    :raises Exception: Exceptions might occurs from the URL format and get request. Or from xml parsing
    """
    try:
        requests.packages.urllib3.disable_warnings()
        response = requests.get(url, verify=False, timeout=timeout)
        parsed_response = json.loads(response.text)
    except NewConnectionError as nce:
        if logger is not None:
            logger.critical(nce.message)
        error_msg = "Http Connection failed."
        raise RuntimeError(error_msg)
    except JSONDecodeError as jerr:
        if logger is not None:
            logger.critical(jerr.message)
        error_msg = f"JSON Decode of {url} failed."
        raise RuntimeError(error_msg)

    return parsed_response

def gen_dict_extract(var, key):
    """
    Extract field from nested dictionary with specific key
    :param var: The dictionary to search(haystack)
    :type var: dict

    :param key: The key we are searching(needle)
    :type key: string

    :return: yields a generator object
    :rtype: Iterator[str]
    """
    if isinstance(var, dict):
        for k, v in var.items():
            if key in k:
                yield v
            if isinstance(v, (dict, list)):
                yield from gen_dict_extract(v, key)
    elif isinstance(var, list):
        for d in var:
            yield from gen_dict_extract(d, key)


def fetch_cert_from_type(metadata_dict, cert_type):
    """
    Fetch X509 per type. Supported types [signing, encryption]
    :param metadata_dict: Metadata passed in dictionary format
    :type metadata_dict: dict
    :param cert_type: The type of Certificate i am looking for
    :type cert_type: str

    :return: dictionary of certificates {type<str>: certificate<str>}
    :rtype: dict
    :todo use enumarators instead of fixed values for all,encryption,signing
    """
    try:
        x509_list_gen = gen_dict_extract(metadata_dict, 'KeyDescriptor')
        x509_list = next(x509_list_gen)
        x509_dict = {}
        # If all is chosen then return a list with all the certificates
        if cert_type == 'all':
            for x509_elem_obj in x509_list:
                # if there is no certificate type then x509_elem_obj will not actually be a dictionary
                if isinstance(x509_elem_obj, dict):
                    mcert_type = ['unknown', x509_elem_obj.get('@use')]['@use' in x509_elem_obj]
                    x509_dict[mcert_type] = x509_elem_obj.get('ds:KeyInfo').get('ds:X509Data').get(
                        'ds:X509Certificate')
                else:
                    x509_dict['unknown'] = x509_list.get('ds:KeyInfo').get('ds:X509Data').get('ds:X509Certificate')
            return x509_dict
        else:  # If not then return the certificate of the type requested
            for x509_elem_obj in x509_list:
                # if there is no certificate type then x509_elem_obj will not actually be a dictionary
                if isinstance(x509_elem_obj, dict):
                    if x509_elem_obj.get('@use') != cert_type:
                        continue
                    x509_dict[x509_elem_obj.get('@use')] = x509_elem_obj.get('ds:KeyInfo').get('ds:X509Data').get(
                        'ds:X509Certificate')
                else:
                    x509_dict['unknown'] = x509_list.get('ds:KeyInfo').get('ds:X509Data').get('ds:X509Certificate')
                return x509_dict
                # If no Certificate available raise an exception
        raise Exception("No X509 certificate of type:%s found" % cert_type)
    except Exception as e:
        # Log the title of the view
        raise Exception(e.args[0]) from e


def evaluate_single_certificate(x509):
    """
    Translate the certificate to its attributes. Calculate the days to expiration
    :param x509: body of x509
    :type x509: string

    :return: Days to Expiration
    :rtype: int

    :return: Certificates Attributes
    :rtype: dict
    """
    try:
        x509_str = "-----BEGIN CERTIFICATE-----\n" + x509 + "\n-----END CERTIFICATE-----\n"
        # Decode the x509 certificate
        x509_obj = crypto.load_certificate(crypto.FILETYPE_PEM, x509_str)
        certData = {
            'Subject': dict(x509_obj.get_subject().get_components()),
            'Issuer': dict(x509_obj.get_issuer().get_components()),
            'serialNumber': x509_obj.get_serial_number(),
            'version': x509_obj.get_version(),
            'not Before': datetime.strptime(x509_obj.get_notBefore().decode(), '%Y%m%d%H%M%SZ'),
            'not After': datetime.strptime(x509_obj.get_notAfter().decode(), '%Y%m%d%H%M%SZ'),
        }
        certData['Subject'] = {y.decode(): certData['Subject'].get(y).decode() for y in certData['Subject'].keys()}
        certData['Issuer'] = {y.decode(): certData['Issuer'].get(y).decode() for y in certData['Issuer'].keys()}

    except Exception as e:
        # Throw the exception back to the main thread to catch
        raise Exception from e

    cert_expire = certData['not After']
    now = datetime.fromtimestamp(mktime(gmtime(time())))
    expiration_days = (cert_expire - now).days

    return expiration_days, certData


def start_ticking():
    """Start timing"""
    return t.time()


def stop_ticking(tik_start):
    """
    Stop timing
    :return: time in seconds, -1 if tik_start is None
    :rtype: float
    """
    if not tik_start:
        return -1

    return t.time() - tik_start


def get_nagios_status_n_code(var_chk, warning_th, critical_th, logger=None):
    """
    Return the status and the exit code  needed by Nagios
    :param var_chk: Value to check
    :type var_chk: int

    :param warning_th: Warning threshold
    :type warning_th: int

    :param critical_th: Critical threshold
    :type critical_th: int

    :param logger: Logger object. Pass if you want to log
    :type Logger: Logger Object

    :return: status, code NagiosStatusCode value and exit code
    :rtype: NagiosStatusCode, int
    """
    if var_chk > warning_th:
        status = NagiosStatusCode.OK.name
        code = NagiosStatusCode.OK.value
    elif warning_th > var_chk > critical_th:
        status = NagiosStatusCode.WARNING.name
        code = NagiosStatusCode.WARNING.value
    elif var_chk < critical_th:
        status = NagiosStatusCode.CRITICAL.name
        code = NagiosStatusCode.CRITICAL.value
    else:
        msg = "State" + NagiosStatusCode.UNKNOWN.name
        if logger is not None:
            logger.info(msg)
        code = NagiosStatusCode.UNKNOWN.value

    return status, code


def get_package_root():
    """Returns project root folder."""
    return pkg_resources.get_distribution('rciam_probes').location


def get_verbosity_level(raw_argument):
    """
    Return the correct logging level
    :param raw_argument: The argument count
    :type raw_argument: int

    :return: log level or -1 if the input is not int
    :rtype: LoggingLevel, int
    """
    if not isinstance(raw_argument, int):
        return -1

    if raw_argument == 0:
        return LoggingLevel.critical.value
    elif raw_argument == 1:
        return LoggingLevel.error.value
    elif raw_argument == 2:
        return LoggingLevel.warning.value
    elif raw_argument == 3:
        return LoggingLevel.info.value
    elif raw_argument >= 4:
        return LoggingLevel.debug.value


def construct_out_filename(args, file_extension):
    """
    Get the argument list from command line and construct the output filename
    :param args: arguments retrieved from command line
    :type args: dict

    :param file_extension: the extension type of the file
    :type file_extension: string

    :return: list of filenames
    :rtype list
    """
    idp_list = args.identity.split(',')
    if isinstance(idp_list, list):
        fname_out_list = []
        for idp in idp_list:
            filename2hash = args.sp + idp + args.hostname
            filename_postfix = hashlib.md5(filename2hash.encode()).hexdigest()
            out_filename_postfix = "out_" + str(filename_postfix) + "." + file_extension
            fname_out_list.append(out_filename_postfix)
        return fname_out_list
    else:
        filename2hash = args.sp + args.identity + args.hostname
        filename_postfix = hashlib.md5(filename2hash.encode()).hexdigest()
        return ["out_" + str(filename_postfix) + "." + file_extension]


def blk_validate_probe_data(raw_data_list):
    """
    :param raw_data_list: List of probe data
    :type raw_data_list: [string]

    :return: code, NagiosStatusCode exit code
    :rtype: NagiosStatusCode, int

    :return: msg, List of messages
    :rtype: [string]

    :return: vtype, List of value types
    :rtype: [string]
    """

    # Always start with a negative code
    # Logic: If at least one successfull
    code = -1
    msg = []
    vtype = []
    for raw_data in raw_data_list:
        validate = timestamp_check(raw_data['date'])
        if not validate:
            raw_data['xcode'] = NagiosStatusCode.UNKNOWN.value
        # Initialize the exit code
        code = raw_data['xcode'] if code < 0 else code
        # If at least one succeeded or in warning state make it a warning
        if code != 0 and raw_data['xcode'] <= 1:
            code = 1
        # todo: What should i choose between critical(2) and unknown(3)

        msg_value = raw_data['value'] if validate else "State " + NagiosStatusCode.UNKNOWN.name + "(Service became Stale)"
        msg.append(raw_data['idp'] + ": " + str(msg_value) + str(raw_data['vtype']))
        vtype.append(str(raw_data['vtype']))

    return code, msg, vtype


def construct_probe_msg(args, value, vtype="s", xcode=0):
    """
    Get the argument list from command line, the outcome of the test and construct the actual message in the desired format
    :param args: arguments retrieved from command line
    :type args: dict

    :param value: the payload of the message
    :type string|number

    :param vtype: the type of the value
    :type vtype: str

    :param xcode: exit code from the experiment. Nagios like. Defaults to success
    :type xcode: int

    :return: message
    :rtype string
    """
    if args.json or args.json_path:
        data = {}
        data['date'] = datetime.now(timezone.utc).timestamp()
        data['value'] = value
        data['vtype'] = vtype
        data['idp'] = args.identity
        data['sp'] = args.sp
        data['hostname'] = args.hostname
        data['xcode'] = xcode
        return json.dumps(data)
    else:
        if type(value) == int or type(value) == float:
            return tpl.login_health_check_nagios_tmpl.substitute(tpl.defaults_login_health_check, time=value,
                                                                 type=vtype)
        else:
            return value


def take_snapshot(driver, logger=None):
    """
    Get Browser/Driver snapsho
    :param driver: geckodriver parameter
    :type drriver: geckodriver object

    :param value: logger object
    :type object
    """

    now = datetime.now()
    # The filename has to end with .png file extension
    filename = 'snapshot_' + now.strftime("%Y-%m-%d-%H:%M:%S") + '.png'
    fnamePath = Path.home().joinpath('html').joinpath('results').joinpath(filename)
    # Convert to string and use
    driver.save_screenshot(str(fnamePath))
    if logger is not None:
        logger.debug("Snapshot saved in path: " + str(fnamePath))


def print_output(args, msg, logger=None):
    """
    Get the argument list from command line and the message, then print the output.
    :param args: arguments retrieved from command line
    :type args: dict

    :param value: message to print
    :type string

    :param value: logger object
    :type object
    """
    if args.json_path:
        filenames = construct_out_filename(args, "json")
        fpath_array = args.json_path.split('/')
        fpath_array = list(filter(None, fpath_array))
        fpath = Path.home().joinpath(*fpath_array)
        if not fpath.is_dir():
            if logger is not None:
                logger.debug(str(fpath) + " does not exist. Creating it.")
            fpath.mkdir(0o755, parents=True, exist_ok=True)
        logger.debug("Write data in path: " + str(fpath))
        for fn in filenames:
            ofile = fpath.joinpath(fn)
            ofile.touch(exist_ok=True)
            ofile.write_text(msg)
    elif args.json:
        filenames = construct_out_filename(args, "json")
        fpath = Path('/').joinpath('var').joinpath('www').joinpath('html')
        if not fpath.is_dir():
            if logger is not None:
                logger.debug(ParamDefaults.JSON_PATH.value + " does not exist")
            print(msg)
            return
        logger.debug("Write data in path: " + str(fpath))
        try:
            for fn in filenames:
                ofile = fpath.joinpath(fn)
                ofile.touch(exist_ok=True)
                ofile.write_text(msg)
        except PermissionError:
            logger.warning("Insufficient permissions to create " + str(fn))

    else:
        print(msg)


def timestamp_check(date, vld_time_window=30):
    """
    :param date: timestamp generated from datetime package
    :type date: str

    :param vld_time_window: time window which will validate the check as true. Represent minutes
    :type int

    :return: validation
    :rtype boolean

    todo: python36 datetime pkg does not recognize the UTC isoformat generated by datetime Python package
    # Changed in version 3.7: When the %z directive is provided to the strptime() method,
    # the UTC offsets can have a colon as a separator between hours, minutes and seconds.
    # For example, '+01:00:00' will be parsed as an offset of one hour. In addition,
    # providing 'Z' is identical to '+00:00'.
    """
    if date is None:
        return False
    # Handle date read from remote
    # It will produce two groups. The second one is the UTC offset, if present.
    dnow = datetime.now(timezone.utc).timestamp()
    ddiff_min = (dnow - date) / 60
    if ddiff_min > vld_time_window:
        return False
    else:
        return True

def evaluate_response_status(browser, args, logger=None):
    """

    :param browser: Webdriver object of Firefox agent
    :type webdriver object

    :param args: arguments retrieved from command line
    :type args: dict

    :param logger: Logger object. Pass if you want to log
    :type Logger: Logger Object

    :raise RuntimeError
    """
    for request in browser.requests:
        if request.response and request.host == args.hostname:
            if request.response.status_code >= 500:
                # Log the host, status, request
                logger.error("Service is down: " + str(request.response.status_code))
                raise RuntimeError('Service unavailable[' + str(request.response.status_code) + ']')
