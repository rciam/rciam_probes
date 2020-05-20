#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import os
import urllib3
import xmltodict

from lib.enums import LoggingDefaults, LoggingLevel


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
        args.log = LoggingDefaults.LOG_FILE.value
    # Set the log verbosity
    if not args.verbose:
        args.verbose = LoggingLevel.info.value
    else:
        args.verbose = getattr(LoggingLevel, args.verbose).value
    # Create the log file if not present
    if not os.path.exists(args.log):
        open(args.log, 'w').close()

    # Create the Logger
    logger = logging.getLogger(__name__)
    logger.setLevel(args.verbose)

    # Create the Handler for logging data to a file
    logger_handler = logging.FileHandler(args.log)
    logger_handler.setLevel(args.verbose)

    # Create a Formatter for formatting the log messages
    logger_formatter = logging.Formatter(LoggingDefaults.LOG_FORMATTER.value)
    # Add the Formatter to the Handler
    logger_handler.setFormatter(logger_formatter)
    # Add the Handler to the Logger
    logger.addHandler(logger_handler)

    return logger


def get_xml(url):
    """
    Get and parse an xml available through a url
    :param url: URL
    :type url: string

    :return: Data parsed from the xml
    :rtype: dict

    :raises Exception: Exceptions might occurs from the URL format and get request. Or from xml parsing
    """
    http = urllib3.PoolManager()
    response = http.request('GET', url)
    data = xmltodict.parse(response.data)
    return data


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
