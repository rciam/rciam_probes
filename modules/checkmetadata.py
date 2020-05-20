#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys
from datetime import datetime
from time import mktime, time, gmtime
from OpenSSL import crypto
# import methods from the lib directory
from lib.enums import NagiosStatusCode, LoggingDefaults
from lib.templates import *
from lib.utils import configure_logger, get_xml, gen_dict_extract


class RciamMetadataCheck:
    __logger = None
    __args = None

    def __init__(self, args=sys.argv[1:]):
        self.__args = parse_arguments(args)
        self.__logger = configure_logger(self.__args)

    def check_cert(self):
        # if the user gave no url then exit
        if not self.__args.url:
            self.__logger.error("URL not found. Please provide metadata URL")
            exit(NagiosStatusCode.UNKNOWN.value)

        # log my running command
        self.__logger.info(' '.join([(repr(arg) if ' ' in arg else arg) for arg in sys.argv]))
        try:
            metadataDict = get_xml(self.__args.url)
            x509Gen = gen_dict_extract(metadataDict, 'X509Certificate')
            x509 = next(x509Gen)
            # create crt string
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
            # Log the title of the view
            self.__logger.error(e)
            exit(NagiosStatusCode.UNKNOWN.value)

        cert_expire = certData['not After']
        now = datetime.fromtimestamp(mktime(gmtime(time())))
        expiration_days = (cert_expire - now).days
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
            print(msg)
            exit(NagiosStatusCode.UNKNOWN.value)
        msg = cert_health_check_tmpl.substitute(
            status=status,
            subject=certData['Subject']['CN'],
            issuer=certData['Issuer']['CN'],
            not_after=certData['not After'],
            expiration_days=expiration_days,
            warning=self.__args.warning,
            critical=self.__args.critical
        )
        # print to output
        print(msg)
        # print to logs
        self.__logger.info(msg)
        exit(code)


# Parse the arguments from the command line
def parse_arguments(args):
    parser = argparse.ArgumentParser(description="Cert Check Probe for Argo")

    parser.add_argument('--log', '-l', dest="log", help='Logfile full path', default= LoggingDefaults.LOG_FILE.value)
    parser.add_argument('--verbose', '-v', dest="verbose", help='Set log verbosity', choices=['debug', 'info', 'warning', 'error', 'critical'])
    parser.add_argument('--warning', '-w', dest="warning", help='Warning threshold', type=int, default=30)
    parser.add_argument('--critical', '-c', dest="critical", help='Critical threshold', type=int, default=10)
    parser.add_argument('--url', '-u', dest="url", required=True,
                        help='Metadata URL, e.g. https://example.com/saml2IDp/proxy.xml')

    return parser.parse_args(args)


# Entry point
if __name__ == "__main__":
    check = RciamMetadataCheck()
    check.check_cert()
