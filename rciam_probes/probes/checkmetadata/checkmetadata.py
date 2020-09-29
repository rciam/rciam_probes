#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys
import pkg_resources
from argparse import ArgumentParser
# import methods from the lib directory
from rciam_probes.shared.enums import *
from rciam_probes.shared.templates import *
from rciam_probes.shared.utils import *


class RciamMetadataCheck:
    __logger = None
    __args = None
    __msg = ''
    __ncode = -1
    __url = None
    __protocol = None
    __timeout = None

    def __init__(self, args=sys.argv[1:]):
        self.__args = parse_arguments(args)
        self.__logger = configure_logger(self.__args)
        self.__protocol = 'http' if self.__args.port == 80 else 'https'
        self.__timeout = self.__args.timeout
        self.__url =  self.__protocol +\
                      '://' + self.__args.hostname +\
                      '/' + self.__args.endpoint
        self.__logger.info('Metadata URL: %s' % (self.__url))

    def check_cert(self):
        # log my running command
        self.__logger.info(' '.join([(repr(arg) if ' ' in arg else arg) for arg in sys.argv]))

        try:
            metadata_dict = get_xml(self.__url, self.__timeout)
            # Find the certificate by type
            x509_dict = fetch_cert_from_type(metadata_dict, self.__args.certuse)
            if len(x509_dict) > 1:
                msg_list = []
                for certuse, value in x509_dict.items():
                    expiration_days, certData = evaluate_single_certificate(value)
                    status, code = get_nagios_status_n_code(expiration_days, self.__args.warning, self.__args.critical, self.__logger)
                    msg_list.append(cert_health_check_all_tmpl.substitute(defaults_cert_health_check_all,
                                                                          type=certuse,
                                                                          status=status))
                    self.__ncode = [self.__ncode, code][self.__ncode < code]
                separator = ', '
                self.__msg = separator.join(msg_list)
                # Add the performance data
                self.__msg += " | 'SSL Metadata Cert Status'=" + str(self.__ncode)
            else:
                expiration_days, certData = evaluate_single_certificate(list(x509_dict.values())[0])
                status, code = get_nagios_status_n_code(expiration_days, self.__args.warning, self.__args.critical, self.__logger)
                self.__ncode = code
                self.__msg = cert_health_check_tmpl.substitute(defaults_cert_health_check,
                                                               type=list(x509_dict.keys())[0],
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
    parser = argparse.ArgumentParser(description="Cert Check Probe for RCIAM")

    parser.add_argument('--log', '-l', dest="log", help='Logfile full path', default=ParamDefaults.LOG_FILE.value)
    parser.add_argument('--verbose', '-v', dest="verbose", help='Set log verbosity',
                        choices=['debug', 'info', 'warning', 'error', 'critical'])
    parser.add_argument('--port', '-p', dest="port", help='Set service port',
                        choices=[80, 443], default=443, type=int)
    parser.add_argument('--warning', '-w', dest="warning", help='Warning threshold', type=int, default=30)
    parser.add_argument('--critical', '-c', dest="critical", help='Critical threshold', type=int, default=10)
    parser.add_argument('--certuse', '-s', dest="certuse", help='Certificate Use', default='signing',
                        choices=['signing', 'encryption', 'all'])
    parser.add_argument('--hostname', '-H', dest="hostname", required=True,
                        help='Domain, protocol assumed to be https, e.g. example.com')
    parser.add_argument('--endpoint', '-e', dest="endpoint", required=True,
                        help='Metadata endpoint, e.g. proxy/saml2/idp/metadata.php')
    parser.add_argument('--timeout', '-t', dest="timeout", type=int,
                        help='Timeout after x seconds.Default is 5s.', default=5)
    parser.add_argument('--logowner', '-o', dest="logowner", default=ParamDefaults.LOG_OWNER.value,
                        help='Owner of the log file rciam_probes.log under /var/log/rciam_probes/. Default owner is nagios user.')
    parser.add_argument('--console', '-C', dest="console",
                        help='No Value needed. The presence of the flag indicates log output in stdout',
                        action='store_true')

    return parser.parse_args(args)


# Entry point
if __name__ == "__main__":
    check = RciamMetadataCheck()
    check.check_cert()
