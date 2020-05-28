#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys
from argparse import ArgumentParser
# import methods from the lib directory
from lib.enums import NagiosStatusCode, LoggingDefaults
from lib.templates import *
from lib.utils import configure_logger, get_xml, fetch_cert_from_type, evaluate_single_certificate


class RciamMetadataCheck:
    __logger = None
    __args = None
    __msg = ''
    __ncode = -1

    def __init__(self, args=sys.argv[1:]):
        self.__args = parse_arguments(args)
        self.__logger = configure_logger(self.__args)

    def get_nagios_status_n_code(self, expiration_days, certData):
        """
        Return the status and the exit code  needed by Nagios
        :param expiration_days: Days remaining for the certificate to expire
        :type expiration_days: int

        :param certData: Attributes of the Certificate after translation
        :type certData: dict

        :return: status, code NastiosStatusCode value and exit code
        :rtype: NagiosStatusCode, int
        """
        if expiration_days > self.__args.warning:
            status = NagiosStatusCode.OK.name
            code = NagiosStatusCode.OK.value
        elif self.__args.warning > expiration_days > self.__args.critical:
            status = NagiosStatusCode.WARNING.name
            code = NagiosStatusCode.WARNING.value
        elif expiration_days < self.__args.critical:
            status = NagiosStatusCode.CRITICAL.name
            code = NagiosStatusCode.CRITICAL.value
        else:
            msg = "State" + NagiosStatusCode.UNKNOWN.name
            self.__logger.info(msg)
            code = NagiosStatusCode.UNKNOWN.value

        return status, code

    def check_cert(self):
        """Check metadata's certificate"""
        if not self.__args.url:
            self.__logger.error("URL not found. Please provide metadata URL")
            exit(NagiosStatusCode.UNKNOWN.value)

        # log my running command
        self.__logger.info(' '.join([(repr(arg) if ' ' in arg else arg) for arg in sys.argv]))

        try:
            metadata_dict = get_xml(self.__args.url)
            # Find the certificate by type
            x509_dict = fetch_cert_from_type(metadata_dict, self.__args.ctype)
            if len(x509_dict) > 1:
                msg_list = []
                for ctype, value in x509_dict.items():
                    expiration_days, certData = evaluate_single_certificate(value, self.__logger)
                    status, code = self.get_nagios_status_n_code(expiration_days, certData)
                    msg_list.append(cert_health_check_all_tmpl.substitute(type=ctype,status=status))
                    self.__ncode = [self.__ncode, code][self.__ncode < code]
                separator = ', '
                self.__msg = separator.join(msg_list)
                # Add the performance data
                self.__msg += " | 'SSL Metadata Cert Status'=" + str(self.__ncode)


            else:
                expiration_days, certData = evaluate_single_certificate(list(x509_dict.values())[0], self.__logger)
                status, code = self.get_nagios_status_n_code(expiration_days, certData)
                self.__ncode = code
                self.__msg = cert_health_check_tmpl.substitute( type=self.__args.ctype,
                                                                status=status,
                                                                subject=certData['Subject']['CN'],
                                                                issuer=certData['Issuer']['CN'],
                                                                not_after=certData['not After'],
                                                                expiration_days=expiration_days,
                                                                warning=self.__args.warning,
                                                                critical=self.__args.critical
                                                              )

        except Exception as e:
            self.__logger.error(e)
            print("Unknown State")
            exit(NagiosStatusCode.UNKNOWN.value)


        # print to output
        print(self.__msg)
        # print to logs
        self.__logger.info(self.__msg)
        exit(self.__ncode)


def parse_arguments(args):
    """
    Parse the arguments provided in the command line
    :param args: list of arguments
    :type args: list
    :return: argument object
    :rtype: ArgumentParser
    """
    parser = argparse.ArgumentParser(description="Cert Check Probe for RCIAM")  # type: ArgumentParser

    parser.add_argument('--log', '-l', dest="log", help='Logfile full path', default=LoggingDefaults.LOG_FILE.value)
    parser.add_argument('--verbose', '-v', dest="verbose", help='Set log verbosity',
                        choices=['debug', 'info', 'warning', 'error', 'critical'])
    parser.add_argument('--warning', '-w', dest="warning", help='Warning threshold', type=int, default=30)
    parser.add_argument('--critical', '-c', dest="critical", help='Critical threshold', type=int, default=10)
    parser.add_argument('--ctype', '-t', dest="ctype", help='Certificate type', default='signing',
                        choices=['signing', 'encryption', 'all'])
    parser.add_argument('--url', '-u', dest="url", required=True,
                        help='Metadata URL, e.g. https://example.com/saml2IDp/proxy.xml')

    return parser.parse_args(args)


# Entry point
if __name__ == "__main__":
    check = RciamMetadataCheck()
    check.check_cert()
