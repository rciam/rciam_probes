#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import re
import time as t
from urllib.parse import *

from selenium import webdriver
from selenium.common.exceptions import *
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from json.decoder import JSONDecodeError

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
    __profile = None
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
        # We do not need to create a web object if we are fetching the data from a url
        if self.__args.inlocation is None:
            # configure the web driver
            self.__init_browser()

    def __init_browser(self):
        """ configure the web driver """
        self.__options = webdriver.FirefoxOptions()
        self.__options.headless = True
        self.__options.accept_insecure_certs = True
        self.__geckodriver_binary = self.__args.geckodriver
        self.__firefox_binary = FirefoxBinary(self.__args.firefox)
        # Set firefox profile
        self.__profile = webdriver.FirefoxProfile()
        firefox_profile(self.__profile)
        if self.__browser is not None:
            self.__browser.close()

        if(self.__args.console):
            self.__browser = webdriver.Firefox(options=self.__options,
                                               firefox_binary=self.__firefox_binary,
                                               firefox_profile=self.__profile,
                                               executable_path=self.__geckodriver_binary,
                                               log_path=os.path.devnull)
        else:
            self.__browser = webdriver.Firefox(options=self.__options,
                                               firefox_binary=self.__firefox_binary,
                                               firefox_profile=self.__profile,
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
        self.__browser.get(self.__args.sp)
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
                self.__logger.warning('No simplesamlPHP modules found. Continue...')
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
                self.__logger.warning(AuthenticateTxt.AlertFailed.value)
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
            self.__logger.warning('Idp has no consent page. Continue...')

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
        if self.__args.rs is not None:
            landing_page = self.__args.rs
        else:
            landing_page = self.__args.sp
        self.__wait.until(
            lambda driver: self.__browser.current_url.strip('/').find(landing_page.strip('/')) == 0)
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
            if self.__args.inlocation is None:
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
                msg_value = round(stop_ticking(self.__start_time), 2)
                # msg_value = login_health_check_nagios_tmpl.substitute(defaults_login_health_check, time=login_finished)
            else:
                raw_data = get_json(self.__args.inlocation + "/" + construct_out_filename(self.__args, "json"))
                msg_value = raw_data['value']
                msg_type = raw_data['vtype']
                code = NagiosStatusCode.OK.value
            code = NagiosStatusCode.OK.value
        except TimeoutException:
            msg_value = "State " + NagiosStatusCode.UNKNOWN.name + "(Request Timed out)"
            # Log print here
            code = NagiosStatusCode.UNKNOWN.value
        except ErrorInResponseException:
            msg_value = "State " + NagiosStatusCode.UNKNOWN.name + "(HTTP status code:)"
            # Log print here
            code = NagiosStatusCode.UNKNOWN.value
        except JSONDecodeError as e:
            msg_value = "State " + NagiosStatusCode.UNKNOWN.name
            # Log Print here
            code = NagiosStatusCode.UNKNOWN.value
            self.__logger.critical("JSON decode error.JSON invalid format or not available.")
        except Exception as e:
            msg_value = "State " + NagiosStatusCode.UNKNOWN.name
            # Log Print here
            code = NagiosStatusCode.UNKNOWN.value
            self.__logger.critical(e)
        finally:
            if self.__browser is not None:
                self.__browser.quit()
            msg = construct_probe_msg(self.__args, msg_value)
            self.__logger.info(msg)
            print_output(self.__args, msg)
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
    parser.add_argument('--firefox', '-f', dest="firefox", help='Firefox binary full path',
                        default=ParamDefaults.FIREFOX_PATH.value)
    parser.add_argument('--geckodriver', '-g', dest="geckodriver", help='geckodriver binary full path',
                        default=ParamDefaults.GECKODRIVER_PATH.value)
    parser.add_argument('--log', '-l', dest="log", help='Logfile full path', default=ParamDefaults.LOG_FILE.value)
    parser.add_argument('--verbose', '-v', dest="verbose", help='Set log verbosity, levels are -v to -vvvv', action="count",
                         default=0)
    parser.add_argument('--port', '-p', dest="port", help='Set service port',
                        choices=[80, 443], default=443, type=int)
    parser.add_argument('--basic_auth', '-b', dest="basic_auth",
                        help='No Value needed. The presence of the flag indicates login test of Service Account',
                        action='store_true')
    parser.add_argument('--console', '-C', dest="console",
                        help='No Value needed. The presence of the flag indicates log output in stdout',
                        action='store_true')
    parser.add_argument('--json', '-J', dest="json",
                        help='No Value needed. The presence of the flag indicates probe output in /var/www/html directory, in file xxx.json',
                        action='store_true')
    parser.add_argument('--timeout', '-t', dest="timeout", help='Timeout after x amount of seconds. Defaults to 5s.',
                        type=int, default=5)
    parser.add_argument('--inlocation', '-e', dest="inlocation", help='URL location to get raw monitoring data from.',
                        type=str, required=False)
    parser.add_argument('--sp', '-s', dest="sp",
                        help='Service Provider Login Authentication Protected URL, e.g. https://example.com/ssp/module.php/core/authenticate.php'
                             '?as=example-sp',
                        required=True)
    parser.add_argument('--rs', '-r', dest="rs",
                        help='Service Provider Landing Page URL. If not provided the prove will assume that the landing page is the same as the Authentication URL. This is true for the case of SimpleSamlPHP Dummy SPs.')
    parser.add_argument('--idp', '-i', dest="identity",
                        help='AuthnAuthority URL, e.g. https://idp.admin.grnet.gr/idp/shibboleth',
                        required=True)
    parser.add_argument('--hostname', '-H', dest="hostname", required=True,
                        help='Domain, protocol assumed to be https, e.g. example.com')
    parser.add_argument('--logowner', '-o', dest="logowner", default=ParamDefaults.LOG_OWNER.value,
                        help='Owner of the log file rciam_probes.log under /var/log/rciam_probes/. Default owner is nagios user.')

    return parser.parse_args(args)

def firefox_profile(firefox_profile):
    """
    Apply firefox profile configuration
    :param firefox_profile: firefox geckodriver webdriver.FirefoxProfile()
    :type firefox_profile:  FirefoxProfile object
    """
    firefox_profile.set_preference("network.http.pipelining", True)
    firefox_profile.set_preference("network.http.proxy.pipelining", True)
    firefox_profile.set_preference("network.http.pipelining.maxrequests", 8)
    firefox_profile.set_preference("content.notify.interval", 500000)
    firefox_profile.set_preference("content.notify.ontimer", True)
    firefox_profile.set_preference("content.switch.threshold", 250000)
    # firefox_profile.set_preference("browser.cache.memory.capacity", 65536)  # Increase the cache capacity.
    firefox_profile.set_preference("browser.startup.homepage", "about:blank")
    firefox_profile.set_preference("reader.parse-on-load.enabled", False)  # Disable reader, we won't need that.
    firefox_profile.set_preference("browser.pocket.enabled", False)  # Duck pocket too!
    firefox_profile.set_preference("loop.enabled", False)
    firefox_profile.set_preference("browser.chrome.toolbar_style", 1)  # Text on Toolbar instead of icons
    firefox_profile.set_preference("browser.display.show_image_placeholders", False)  # Don't show thumbnails on not loaded images.
    firefox_profile.set_preference("browser.display.use_document_colors", False)  # Don't show document colors.
    firefox_profile.set_preference("browser.display.use_document_fonts", 0)  # Don't load document fonts.
    firefox_profile.set_preference("browser.display.use_system_colors", True)  # Use system colors.
    firefox_profile.set_preference("browser.formfill.enable", False)  # Autofill on forms disabled.
    firefox_profile.set_preference("browser.helperApps.deleteTempFileOnExit", True)  # Delete temprorary files.
    firefox_profile.set_preference("browser.shell.checkDefaultBrowser", False)
    firefox_profile.set_preference("browser.startup.homepage", "about:blank")
    firefox_profile.set_preference("browser.startup.page", 0)  # blank
    firefox_profile.set_preference("browser.tabs.forceHide", True)  # Disable tabs, We won't need that.
    firefox_profile.set_preference("browser.urlbar.autoFill", False)  # Disable autofill on URL bar.
    firefox_profile.set_preference("browser.urlbar.autocomplete.enabled", False)  # Disable autocomplete on URL bar.
    firefox_profile.set_preference("browser.urlbar.showPopup", False)  # Disable list of URLs when typing on URL bar.
    firefox_profile.set_preference("browser.urlbar.showSearch", False)  # Disable search bar.
    firefox_profile.set_preference("extensions.checkCompatibility", False)  # Addon update disabled
    firefox_profile.set_preference("extensions.checkUpdateSecurity", False)
    firefox_profile.set_preference("extensions.update.autoUpdateEnabled", False)
    firefox_profile.set_preference("extensions.update.enabled", False)
    firefox_profile.set_preference("general.startup.browser", False)
    firefox_profile.set_preference("plugin.default_plugin_disabled", False)
    firefox_profile.set_preference("permissions.default.image", 2)
    firefox_profile.set_preference('browser.cache.disk.enable', False)
    firefox_profile.set_preference('browser.cache.memory.enable', False)
    firefox_profile.set_preference('browser.cache.offline.enable', False)


# Entry point
if __name__ == "__main__":
    check = RciamHealthCheck()
    check.check_login()
