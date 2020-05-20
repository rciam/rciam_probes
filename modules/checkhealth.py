#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys
import time
from selenium import webdriver
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
from urllib.parse import *

# import methods from the lib directory
from lib.enums import NagiosStatusCode, LoggingDefaults, LoggingLevel
from lib.templates import *
from lib.utils import configure_logger


class RciamHealthCheck:
    __browser = None
    __options = None
    __wait = None
    __start_time = None
    __args = None
    __nagios_msg = None
    __logger = None

    def __init__(self, args=sys.argv[1:]):
        """Initialize"""
        self.__args = parse_arguments(args)
        # configure the logger
        self.__logger = configure_logger(self.__args)
        # configure the web driver
        options = webdriver.FirefoxOptions()
        options.add_argument('--headless')
        firefox_binary = FirefoxBinary(self.__args.firefox)
        if self.__browser is not None:
            self.__browser.close()
        self.__browser = webdriver.Firefox(options=options,
                                           firefox_binary=firefox_binary,
                                           executable_path=r'../driver/geckodriver',
                                           log_path=self.__args.log)
        self.__wait = WebDriverWait(self.__browser, self.__args.delay)

    def __hide_cookie_policy(self):
        """Hide the cookie policy banner"""
        cookie_soup = BeautifulSoup(self.__browser.page_source, 'html.parser')
        cookie_div = cookie_soup.find(id='cookies')
        if cookie_div:
            self.__wait.until(EC.element_to_be_clickable((By.ID, "js-accept-cookies")))
            cookie_banner = self.__browser.find_element_by_id("cookies")
            self.__browser.execute_script("arguments[0].setAttribute('style','display: none;')", cookie_banner)
            # Wait until the cookie banner hides
            self.__wait.until(EC.invisibility_of_element_located((By.ID, 'cookies')))

    def __wait_for_spinner(self):
        """Wait for the loading spinner to disappear"""
        try:
            self.__wait.until(EC.invisibility_of_element_located((By.ID, 'loader')))
        except TimeoutException:
            self.__logger.warning('No loader found.Ignore and continue.')

    def __print_user_attributes(self):
        """
        This method iterates over the user attributes fetched by the proxy. It only applies to
        dummy SPs created by simplesamlPHP
        """
        spSoup = BeautifulSoup(self.__browser.page_source, 'html.parser')
        user_attributes = spSoup.find(id='table_with_attributes').find_all('tr')
        # todo: Check if we release all the attributes. Attributes are in columns[0].find('tt').text
        for row in user_attributes:
            columns = row.find_all('td')
            self.__logger.info("%s(Attribute) => %s" % (columns[0].find('tt').text, columns[1].text))

    def __start_ticking(self):
        """Start timing"""
        self.__start_time = time.time()

    def __stop_ticking(self):
        """
        Stop timing
        :return: time in seconds, -1 if __start_time is None
        :rtype: float
        """
        if not self.__start_time:
            return -1

        return time.time() - self.__start_time

    def __sp_redirect_disco_n_click(self):
        """Discovery Service View"""
        self.__browser.get(self.__args.service)
        # Log the title of the view
        self.__logger.debug(self.__browser.title)
        # urlencode idpentityid
        idp_entity_id_url_enc = quote(self.__args.identity, safe='')
        selector_callable = "a[href*='%s']" % (idp_entity_id_url_enc)
        # Find the hyperlink
        self.__wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector_callable)))
        # Wait until it is clickable
        self.__wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector_callable)))
        self.__wait_for_spinner()
        self.__hide_cookie_policy()
        # Select IdP defined in the params
        self.__browser.find_element_by_css_selector(selector_callable).click()

    def __accept_all_ssp_modules(self):
        """
        simplesamlPHP View. Accept all modules.
        :raises TimeoutException: if the elements fail to load
        """
        ssp_modules = True
        while ssp_modules:
            self.__wait.until(EC.presence_of_element_located((By.XPATH, "//form[1]")))
            self.__wait.until(EC.presence_of_element_located((By.ID, "cookies")))
            self.__wait.until(EC.element_to_be_clickable((By.ID, "yesbutton")))
            # Log the title of the view
            self.__logger.debug(self.__browser.title)
            # find if this is the consent page
            soup = BeautifulSoup(self.__browser.page_source, 'html.parser')
            ssp_module_action = soup.find('form').get('action')
            if "getconsent.php" in ssp_module_action:
                ssp_modules = False
            # Now click yes on the form and proceed
            continue_btn = self.__browser.find_element_by_id("yesbutton")
            if continue_btn.is_enabled():
                self.__wait_for_spinner()
                self.__hide_cookie_policy()
                continue_btn.click()

    def __idp_authenticate(self):
        """
        Authenticate to IdP
        - Selenium does not return http status codes. Related
          issue(https://github.com/seleniumhq/selenium-google-code-issue-archive/issues/141)
        :raises TimeoutException: if the elements fail to load
        """
        self.__wait.until(EC.presence_of_element_located((By.ID, 'username')))
        username = self.__browser.find_element_by_id('username')
        username.clear()
        username.send_keys(self.__args.username)
        self.__wait.until(EC.presence_of_element_located((By.ID, 'password')))
        password = self.__browser.find_element_by_id('password')
        password.clear()
        password.send_keys(self.__args.password)

        # Log the title of the view
        self.__logger.debug(self.__browser.title)
        self.__wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
        # for the Grnet Identity Provider the submit function is not working
        self.__browser.find_element_by_css_selector("form button[type='submit']").click()
        # Get the source code from the page and check if authentication failed

    def __get_attrs_checking_dummy_sps(self):
        """Get the attributes available in the dummy SP configured with simplesamlPHP"""
        self.__wait.until(EC.presence_of_element_located((By.ID, "content")))
        self.__wait.until(EC.presence_of_all_elements_located((By.ID, "table_with_attributes")))
        self.__print_user_attributes()

    def __verify_sp_home_page_loaded(self):
        """
        Verify that the Service Providers Home page loaded successfully
        :raises TimeoutException: if the elements fail to load
        """
        self.__wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
        self.__wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div")))

    def check_login(self):
        """Check the login flow"""
        self.__logger.info(' '.join([(repr(arg) if ' ' in arg else arg) for arg in sys.argv]))
        # start counting progress time
        self.__start_ticking()
        try:
            # Go to Discovery Service and choose your Identity Provider
            self.__sp_redirect_disco_n_click()
            # Authenticate
            self.__idp_authenticate()
            # You came back from the Idp. Iterate over all SSP modules and press continue
            self.__accept_all_ssp_modules()
            # Verify that the SPs home page loaded
            self.__verify_sp_home_page_loaded()
            code = NagiosStatusCode.OK.value
            msg = login_health_check_tmpl.substitute(time=round(self.__stop_ticking(), 2))
        except TimeoutException:
            msg = "State " + NagiosStatusCode.UNKNOWN.name + "(Request Timed out)"
            # Log print here
            code = NagiosStatusCode.UNKNOWN.value
        except Exception as e:
            msg = "State " + NagiosStatusCode.UNKNOWN.name
            # Log Print here
            code = NagiosStatusCode.UNKNOWN.value
            self.__logger.error(e)
        finally:
            self.__browser.quit()
            self.__logger.info(msg)
            print(msg)
            exit(code)


def parse_arguments(args):
    """
    Parse the arguments provided in the command line
    :param args: list of arguments
    :type args: list
    :return: argument object
    :rtype: ArgumentParser
    """
    parser = argparse.ArgumentParser(description="Health Check Probe for RCIAM")

    parser.add_argument('--username', '-u', dest="username", help='IdP username', required=True)
    parser.add_argument('--password', '-p', dest="password", help='Idp password', required=True)
    parser.add_argument('--firefox', '-f', dest="firefox", help='Firefox binary full path', required=True)
    parser.add_argument('--log', '-l', dest="log", help='Logfile full path', default= LoggingDefaults.LOG_FILE.value)
    parser.add_argument('--verbose', '-v', dest="verbose", help='Set log verbosity', choices=['debug', 'info', 'warning', 'error', 'critical'])
    parser.add_argument('--delay', '-d', dest="delay", help='Maximum delay threshold when loading web page document',
                        type=int, default=10)
    parser.add_argument('--service', '-s', dest="service",
                        help='Service Provider Login, e.g. https://snf-666522.vm.okeanos.grnet.gr/ssp/module.php/core/authenticate.php?as=egi-sp',
                        required=True)
    parser.add_argument('--identity', '-i', dest="identity", help='AuthnAuthority URL, e.g. https://idp.admin.grnet.gr/idp/shibboleth',
                        required=True)

    return parser.parse_args(args)

# Entry point
if __name__ == "__main__":
    check = RciamHealthCheck()
    check.check_login()