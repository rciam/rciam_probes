# RCIAM Probes

This repository contains Nagios plugins to check availability of RCIAM Services.

Currently it supports the following probes:
* Metadata Health
* Login Health

## Requirements
* Python ~=3.5
* Pip3
* firefox: ```/usr/bin/firefox -marionette --headless -foreground -no-remote -profile /tmp/rust_mozprofilerYSIK2```
  * Tested with:
    * Browser Version: v76.0.1
    * Browser Version: v77.0.1
  * Webdriver Version(geckodriver): v0.26.0
    * [Download](https://github.com/mozilla/geckodriver/releases) and install the driver in a directory accessible by the script.

## Installation
Clone and install in local repository with venv
```bash
$ python3 setup.py install
```
Make rpm
```bash
make rpm
```
Make tarball
```bash
make sources
```
Clean Make leftovers
```bash
make clean
```
## Usage
### Metadata Health
```bash
checkcert [-h] [-w WARNING] [-c CRITICAL] [-H HOSTNAME] [-e ENDPOINT] [-s CERTUSE] [-l LOG] [-v VERBOSE] [-p PORT] [-t TIMEOUT]

optional arguments:
  -h, --help                          show this help message and exit
  -c CRITICAL,  --critical CRITICAL   remaining days threshold for critical
  -w WARNING,   --warning WARNING     remaining days threshold for warning
  -s CERTUSE,   --certuse CERTUSE     type of certificate {signing, encryption, all}
  -v VERBOSE,   --verbose VERBOSE     level of verboseness in log messages {debug,info,warning,error,critical}
  -l LOG,       --log LOG             the logfile the probe will use to append its messages, provide full path
  -p PORT,      --port PORT           port the probe will target
  -t TIMEOUT,   --timeout TIMEOUT     number of seconds the probe will wait for response before timeout


required arguments:
  -H HOSTNAME,  --hostname HOSTNAME   domain name of the service
  -e ENDPOINT,  --endpoint ENTPOINT   endpoint advertising the metadata
```
#### CLI command
```bash
sample command: checkcert -w 20 -c 10 -H example.com -e service/Shibboleth.sso/Metadata -t signing

sample output:  SSL_CERT(signing) OK - x509 certificate 'test-eosc-hub.ggus.eu' from 'KIT-CA' is valid until 2022-05-17 10:00:00 (expires in 727 days) | 'SSL Metadata Cert'=727;20;10;0;3650
```
For the case of type:all the output will be different
```bash
sample command: checkcert -H example.com -e proxy/saml2/idp/metadata.php -w 20 -c 10 -t all

sample output:  SSL_CERT(signing) OK, SSL_CERT(encryption) OK | 'SSL Metadata Cert Status'=0
```
### Login Health
```bash
checklogin [-h] [-u USERNAME] [-p PASSWORD] [-f FIREFOX] [-i IDENTITY] [-s SERVICE PROVIDER] [-b|--basic_auth]
          [-t TIMEOUT] [-v VERBOSE] [-l LOG] [-H HOSTNAME] [-p PORT] [-r SERVICE PROVIDER]

optional arguments:
  -h,                  --help                      show this help message and exit
  -t TIMEOUT,          --timeout TIMEOUT           number of seconds the probe will wait for response before timeout
  -v VERBOSE,          --verbose VERBOSE           level of verboseness in log messages {debug,info,warning,error,critical}
  -l LOG,              --log LOG                   the logfile the probe will use to append its messages, provide full path
  -p PORT,             --port PORT                 port the probe will target
  -b,                  --basic_auth                login flow with Basic Authentication
  -f FIREFOX,          --firefox FIREFOX           firefox binary full path
  -g GECKODRIVER,      --geckodriver GECKODRIVER   full path of the geckodriver executable(binary included)
  -r SERVICE,          --rp RP                     full URL of the Service Provider's Landing Page after a successfull authentication

required arguments:
  -u USERNAME,         --username USERNAME         username of the user to be authenticated
  -a PASSWORD,         --password PASSWORD         password of the user to be authenticated
  -i IDENTITY,         --idp IDENTITY              csv list of entityID URL of the identity provider, e.g. https://idp.example.com/idp/shibboleth,https://egi.eu/idp/shibboleth. Each IdP entry represents a hop towards authentication during a login flow.
  -s SERVICE PROVIDER, --sp SP                     full URL of the Service Provider's AUTHENTICATION link the probe will test
  -H HOSTNAME,         --hostname HOSTNAME         domain name of the service
```
#### CLI command
## Form Based Logins
```bash
sample command: checklogin -t 20 -v debug -u $USER -a $PASSWORD -s https://example.com/ssp/module.php/core/authenticate.php?as=test-sp
                           -i https://idp.example.com/idp/shibboleth -H example.com -g /path/to/geckodriver

sample output:  SP Login succeeded(14.92sec time) | 'Login'=14.92s
```
## Basic Authentication Logins
```bash
sample command: checklogin -s https://sp.example.com/ssp/module.php/core/authenticate.php?as=test-sp -i https://idp.example.com/idp/shibboleth
                            -f /usr/bin/firefox -v debug -t 20 -g /path/to/geckodriver -u $USER -a $PASSWORD --basic_auth

sample output:  SP Login succeeded(14.92sec time) | 'Login'=14.92s
```

## What the probes do

### Metadata Certificate Health

Metadata Certificate Health does the following:

* Checks if the x.509 certificate included in the metadata is valid

### Login Health

Login Health does the following:
* Checks if the login flow through the AAI Proxy is successful 

#### SAML Login flow
* The user presses login or follow a symbolic link to the service
* AAI Proxy presents the Discovery Service and the user selects the Identity Provider
* The user authenticates to the IdP
  * Provide username and password and press submit
  * (Optional)Accept Consent page from the Identity Provider
  * SAML Response post back to the proxy
  * A number of simplesamlphp modules will fire. Last will always be the consent page
* The user lands to the home page of the service

The probes:
 * return exit codes and performance data according to Nagios Plugins Specifications
 * (installing with rpm)create the directory structure rciam_probes/rciam_probes.log under the /var/log and all output is redirected there.
 ```bash
/var/log/rciam_probes/
`-- rciam_probes.log
```
 * If /var/log/rciam_probes/ path is not available during probe execution, then the probe will create it under the user's home directory
 ```bash
/home/user/var/log/rciam_probes/
`-- rciam_probes.log
```

## License
Licensed under the Apache 2.0 license, for details see [LICENSE](https://github.com/rciam/rciam_probes/blob/master/LICENSE)
