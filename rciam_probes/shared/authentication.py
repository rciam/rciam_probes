import copy
import http

import requests
from bs4 import BeautifulSoup
from requests.auth import HTTPBasicAuth
try:
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.by import By
except ImportError:
    has_selenium = False
else:
    has_selenium = True

def parse_cookies(http_response):
    """
    Read the cookies from the header and add create a dictionary out of them(Morsel type cookies)
    e.g. Set-Cookie: egi_proxy_authtoken=_ae8d125474fc9ac51c93bcc829a2546b40fb6ace14

    :param http_response: Response object returned from the request library
    :type http_response: object

    :return: Morsel type cookies object
    :rtype: SimpleCookie
    """
    cookie_grp = http.cookies.SimpleCookie()
    for h, v in http_response.request.headers.items():
        if 'cookie' in h.lower():
            for cook in v.split(','):
                cookie_grp.load(cook)
    return cookie_grp


def transfer_driver_cookies_to_request(cookies):
    """
    Extract the cookies to a format that the request library understands
    :param cookies: This should be a driver cookie. Obtained with the command my_driver.get_cookies()
    :type cookies: dict

    :return: Cookies dictionary suitable for a requests lib object
    :rtype: dict
    """
    return {i['name']: i['value'] for i in cookies}


def append_cookie_to_driver_from_request(http_response, driver_cookies):
    """
    Transfer the cookies from a response made with request lib to the drivers cookies

    :param http_response: Response object returned from the request library
    :type http_response: object

    :param cookies: This should be a driver cookie. Obtained with the command my_driver.get_cookies()
    :type cookies: dict
    """
    resonse_cookies = parse_cookies(http_response)
    if resonse_cookies is None \
            or not resonse_cookies \
            or driver_cookies is None \
            or not driver_cookies:
        return

    dc_cookie = copy.deepcopy(driver_cookies)[0]
    for name, value in resonse_cookies.items():
        dc_cookie = copy.deepcopy(dc_cookie)
        dc_cookie['name'] = name
        dc_cookie['value'] = value.value
        driver_cookies.append(dc_cookie)


def browser_load_cookies(browser, cookies, url):
    """
    :param browser: Webdriver Object
    :type browser: Webdriver Object

    :param cookies: Dictionary of Webdriver compatible cookies
    :type cookies: dict

    :param url: Url i want to load the cookies for
    :type url: string
    """
    if url is None:
        return
    browser.get(url)
    browser.delete_all_cookies()
    WebDriverWait(browser, 3).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a")))
    for cookie in cookies:
        browser.add_cookie(cookie)


def base_auth_login(endpoint, args, cached_cookie, logger=None):
    """
    Perform one hop or two hop Basic authentication with SAML response

    :param endpoint: Login endpoint
    :type endpoint: str

    :param args: command line passed arguments( username, password, ssp authtoken name)
    :type args: ArgumentParser

    :param cached_cookie: Dictionary of Cached Webdriver compatible cookies
    :type cached_cookie: dict

    :param logger: Logger object
    :type logger: Logger

    :return: the last url of submitted request
    :rtype: str
    """
    try:
        last_url = None
        # fixme: i think i do not need to transfer the session. I only need the state here
        session_cache = transfer_driver_cookies_to_request(cached_cookie)
        req_with_session = requests.Session()
        # Authenticate
        r_get = req_with_session.get(endpoint, auth=HTTPBasicAuth(args.username, args.password))
        r_get.raise_for_status()
        last_url = r_get.url
        if logger is not None:
            logger.debug(r_get.url + ' \nAuthenticate::Status:' + str(r_get.status_code))
        append_cookie_to_driver_from_request(r_get, cached_cookie)
        # This now returns the SAMLResponse or not. Check and then proceed
        # This is an auto submit page. We should handle it manually with requests lib
        #     <noscript>
        #         <button type="submit" class="btn">Continue</button>
        #     </noscript>
        soup = BeautifulSoup(r_get.text, 'html.parser')
        # todo:here reload selenium
        if soup.find('input', {'name': 'SAMLResponse'}) is not None:
            # todo: Store/return this and use it for further testing
            SAMLResponse = {
                'SAMLResponse': soup.find('input', {'name': 'SAMLResponse'}).get('value')
            }
            postURL = soup.find('form').get('action')
            # Here we need the old cookie so that we can go back
            r_post = req_with_session.post(url=postURL, data=SAMLResponse, cookies=session_cache)
            r_post.raise_for_status()
            last_url = r_post.url
            if logger is not None:
                logger.debug(r_post.url + ' \nSAMLResponse::Status:' + str(r_post.status_code))
            append_cookie_to_driver_from_request(r_post, cached_cookie)

        return last_url
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code
        if code in [400, 401]:
            raise Exception('Unauthorized Access')
        else:
            raise Exception("Invalid response code: " + str(code))
    except requests.exceptions.RequestException as e:
        raise Exception("Cannot connect to endpoint " + endpoint)
    except Exception as e:
        raise Exception from e
