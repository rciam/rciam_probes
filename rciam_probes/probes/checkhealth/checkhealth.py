#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import re
import sys
from urllib.parse import *

from selenium import webdriver
from selenium.common.exceptions import *
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary

from rciam_probes.shared.authentication import *
# import methods from the lib directory
from rciam_probes.shared.enums import *
from rciam_probes.shared.templates import *
from rciam_probes.shared.utils import *


class RciamHealthCheck:
    __browser = None
    __last_url = None
    __cached_cookies = None
    __options = None
    __wait = None
    __start_time = None
    __args = None
    __nagios_msg = None
    __logger = None
    __firefox_binary = None
    __geckodriver_binary = None

    def __init__(self, args=sys.argv[1:]):
        """Initialize"""
        self.__args = parse_arguments(args)

        # configure the logger
        self.__logger = configure_logger(self.__args)
        # configure the web driver
        self.__init_browser()

    def __init_browser(self):
        """ configure the web driver """
        self.__options = webdriver.FirefoxOptions()
        self.__options.headless = True
        self.__options.accept_insecure_certs = True
        self.__geckodriver_binary = self.__args.geckodriver
        self.__firefox_binary = FirefoxBinary(self.__args.firefox)
        if self.__browser is not None:
            self.__browser.close()

        self.__browser = webdriver.Firefox(options=self.__options,
                                           firefox_binary=self.__firefox_binary,
                                           executable_path=self.__geckodriver_binary,
                                           log_path=self.__args.log)
        self.__wait = WebDriverWait(self.__browser, self.__args.timeout)

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

    def __sp_redirect_disco_n_click(self):
        """Discovery Service View"""
        self.__browser.get(self.__args.service)
        # In case i have a list of hops
        idp_list = self.__args.identity.split(',')
        for idp in idp_list:
            # Log the title of the view
            self.__logger.debug(self.__browser.title)
            # urlencode idpentityid
            idp_entity_id_url_enc = quote(idp, safe='')
            selector_callable = "a[href*='%s']" % (idp_entity_id_url_enc)
            # Find the hyperlink
            self.__wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector_callable)))
            # Wait until it is clickable
            self.__wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector_callable)))
            self.__wait_for_spinner()
            self.__hide_cookie_policy()
            # Cache cookies
            self.__cached_cookies = self.__browser.get_cookies()
            # Select IdP defined in the params
            self.__browser.find_element_by_css_selector(selector_callable).click()

    def __accept_all_ssp_modules(self):
        """
        simplesamlPHP View. Accept all modules.
        :raises TimeoutException: if the elements fail to load
        """
        ssp_modules = True
        while ssp_modules:
            try:
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
                    self.__cached_cookies = self.__browser.get_cookies()
            except TimeoutException:
                self.__logger.info('No simplesamlPHP modules found. Continue...')
                ssp_modules = False

    def __idp_authenticate(self):
        """
        Authenticate to IdP
        - Selenium does not return http status codes. Related
          issue(https://github.com/seleniumhq/selenium-google-code-issue-archive/issues/141)

        - Proxy Response: State information lost, and no way to restart the request
        This error may be caused by:
            Using the back and forward buttons in the web browser.
            Opened the web browser with tabs saved from the previous session.
            Cookies may be disabled in the web browser.
        note: We should not close and re-open the browser driver.

        :raises TimeoutException: if the elements fail to load
        """
        if self.__args.basic_auth:
            # todo: Revisit the implementation approach if there is a solution with browser drivers
            try:
                self.__wait.until(EC.alert_is_present())
                self.__logger.debug(self.__browser.current_url)
                alert = self.__browser.switch_to.alert
                alert.send_keys(self.__args.username)
                alert.send_keys(Keys.TAB)
                alert.send_keys(self.__args.password)
                alert.accept()
            except Exception as e:
                # Tried to authenticate with the alert but failed
                # Trying again with request library in finally
                self.__logger.info(AuthenticateTxt.AlertFailed.value)
            else:
                self.__logger.info(AuthenticateTxt.Success.value)
            finally:
                self.__last_url = self.__browser.current_url
                self.__last_url = base_auth_login(self.__browser.current_url,
                                                  self.__args,
                                                  self.__cached_cookies,
                                                  self.__logger)
                # Load the cookies from Identity Provider authentication
                browser_load_cookies(self.__browser,
                                     self.__cached_cookies,
                                     self.__last_url)
                # Retry with proxy
                self.__browser.get(self.__last_url)
        else:
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
            # Cache cookies
            self.__last_url = self.__browser.current_url
            self.__cached_cookies = self.__browser.get_cookies()
            # Accept the form
            self.__browser.find_element_by_css_selector("form button[type='submit']").click()

    def __idp_shib_consent_page(self):
        """
        If the IdP prompts for explicit consent in order to release the attributes
        This page is a Shibboleth consent page
        Info:
        - Shibboleth consent pages have element: input[type='submit'][value='Accept']
        - simplesamlPHP consent pages have element: button[type='submit'][name='yes']
        """
        try:
            regex_domain = r"^https?:[\/]{2}(.*?)[\/]{1}.*$"
            domain = re.search(regex_domain, self.__args.identity).group(1)
            # Only wait at most 5 seconds.
            WebDriverWait(self.__browser, 5).until(lambda driver: self.__browser.current_url.strip('/').find(domain))
            WebDriverWait(self.__browser, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "form [type='submit'][value='Accept']")))
            # Log the title of the view
            self.__logger.debug(self.__browser.title)
            # Cache cookies
            self.__cached_cookies = self.__browser.get_cookies()
            self.__last_url = self.__browser.current_url
            # Accept the form
            self.__browser.find_element_by_css_selector("form [type='submit'][value='Accept']").click()
            # Get the source code from the page and check if authentication failed
        except TimeoutException:
            self.__logger.info('Idp has no consent page. Continue...')

    def __get_attrs_checking_dummy_sps(self):
        """Get the attributes available in the dummy SP configured with simplesamlPHP"""
        self.__wait.until(EC.presence_of_element_located((By.ID, "content")))
        self.__wait.until(EC.presence_of_all_elements_located((By.ID, "table_with_attributes")))
        self.__print_user_attributes()

    def __verify_sp_home_page_loaded(self):
        """
        Verify that the Service Providers Home page loaded successfully
        :raises TimeoutException: if an element fails to load
        """
        # todo: Load a file here with what the function should expect. If not present run the default below
        # todo: The file should be provided from the command line??
        self.__wait.until(
            lambda driver: self.__browser.current_url.strip('/').find(self.__args.service.strip('/')) == 0)
        # self.__wait.until(
        #     lambda driver: self.__browser.current_url.strip('/').find('https://testvm.agora.grnet.gr/ui') == 0)
        self.__wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "head")))
        self.__wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "title")))
        self.__wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))

        # Log the title of the view
        self.__logger.debug(self.__browser.title + "(" + self.__browser.current_url + ")")

    def check_login(self):
        """Check the login flow"""
        # Find the password argument and remove it
        if '-a' in sys.argv:
            pass_index = sys.argv.index('-a')
            del sys.argv[pass_index:pass_index + 2]
        elif '--password' in sys.argv:
            pass_index = sys.argv.index('--password')
            del sys.argv[pass_index:pass_index + 2]

        self.__logger.info(' '.join([(repr(arg) if ' ' in arg else arg) for arg in sys.argv]))
        # start counting progress time
        self.__start_time = start_ticking()
        try:
            # Go to Discovery Service and choose your Identity Provider
            self.__sp_redirect_disco_n_click()
            # Authenticate
            self.__idp_authenticate()
            # Some IdPs might request explicit consent for the transmitted attributes
            # todo: Currently supporting only Consent pages from Shibboleth IdPs
            self.__idp_shib_consent_page()
            # You came back from the Idp. Iterate over all SSP modules and press continue
            self.__accept_all_ssp_modules()
            # Verify that the SPs home page loaded
            self.__verify_sp_home_page_loaded()
            code = NagiosStatusCode.OK.value
            msg = login_health_check_tmpl.substitute(defaults_login_health_check, time=round(stop_ticking(self.__start_time), 2))
        except TimeoutException:
            msg = "State " + NagiosStatusCode.UNKNOWN.name + "(Request Timed out)"
            # Log print here
            code = NagiosStatusCode.UNKNOWN.value
        except ErrorInResponseException:
            msg = "State " + NagiosStatusCode.UNKNOWN.name + "(HTTP status code:)"
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
    parser.add_argument('--password', '-a', dest="password", help='Idp password', required=True)
    parser.add_argument('--firefox', '-f', dest="firefox", help='Firefox binary full path', required=True)
    parser.add_argument('--geckodriver', '-g', dest="geckodriver", help='geckodriver binary full path', required=True)
    parser.add_argument('--log', '-l', dest="log", help='Logfile full path', default=LoggingDefaults.LOG_FILE.value)
    parser.add_argument('--verbose', '-v', dest="verbose", help='Set log verbosity',
                        choices=['debug', 'info', 'warning', 'error', 'critical'])
    parser.add_argument('--port', '-p', dest="port", help='Set service port',
                        choices=[80, 443], default=443, type=int)
    parser.add_argument('--basic_auth', '-b', dest="basic_auth",
                        help='No Value needed. The precense of the flag indicates login test of Service Account',
                        action='store_true')
    parser.add_argument('--timeout', '-t', dest="timeout", help='Timeout after x amount of seconds. Defaults to 5s.',
                        type=int, default=5)
    parser.add_argument('--sp', '-s', dest="service",
                        help='Service Provider Login, e.g. https://example.com/ssp/module.php/core/authenticate.php'
                             '?as=example-sp',
                        required=True)
    parser.add_argument('--idp', '-i', dest="identity",
	                    help='AuthnAuthority URL, e.g. https://idp.admin.grnet.gr/idp/shibboleth',
                        required=True)
    parser.add_argument('--hostname', '-H', dest="hostname", required=True,
                        help='Domain, protocol assumed to be https, e.g. example.com')

    return parser.parse_args(args)


# Entry point
if __name__ == "__main__":
    check = RciamHealthCheck()
    check.check_login()
