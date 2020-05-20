# RCIAM Probes

This repository contains Nagios plugins to check availability of RCIAM Services.

Currently it supports the following probes:
* Metadata Health
* Login Health

## Requirements
* Python 3.5
* Pip3
* firefox
```bash
/usr/bin/firefox -marionette --headless -foreground -no-remote -profile /tmp/rust_mozprofilerYSIK2
```

## Installation
Install the requirements using pip (preferably in a virtualenv):
```bash
$ pip3 install -r requirements.txt
```

Then use setup.py to install the program:
```bash
$ python setup.py install
```

Make rpm
```bash
make rpm
```

Make tarball
```bash
make sources
```

## Usage
### Metadata Health
```bash
checkcert [-h] [-w WARNING] [-c CRITICAL] [-u URL] [-l LOG] [-v VERBOSE]

optional arguments:
  -h, --help                          show this help message and exit
  -c CRITICAL,  --critical CRITICAL   remaining days threshold for critical
  -w WARNING,   --warning WARNING     remaining days threshold for warning
  -v VERBOSE,   --verbose VERBOSE     level of verboseness in log messages {debug,info,warning,error,critical}
  -l LOG,       --log LOG             the logfile the probe will use to append its messages, provide full path

required arguments:
  -u URL,       --url URL             endpoint advertising the metadata
```
#### CLI command
```bash
sample command: checkcert -w 20 -c 10 -u http://example.com/service/Shibboleth.sso/Metadata

sample output:  SSL_CERT OK - x509 certificate 'test-eosc-hub.ggus.eu' from 'KIT-CA' is valid until 2022-05-17 10:00:00 (expires in 727 days) | 'SSL Metadata Cert'=727;20;10;0;3650
```
### Login Health
```bash
checklogin [-h] [-u USERNAME] [-p PASSWORD] [-f FIREFOX] [-i IDENTITY] [-s SERVICE]
          [-d DELAY] [-v VERBOSE] [-l LOG]

optional arguments:
  -h, --help                          show this help message and exit
  -d DELAY,     --delay DELAY         number of seconds the probe will wait for the page to load
  -v VERBOSE,   --verbose VERBOSE     level of verboseness in log messages {debug,info,warning,error,critical}
  -l LOG,       --log LOG             the logfile the probe will use to append its messages, provide full path

required arguments:
  -u USERNAME,  --username USERNAME   username of the user to be authenticated
  -p PASSWORD,  --password PASSWORD   password of the user to be authenticated
  -f FIREFOX,   --firefox FIREFOX     firefox binary full path
  -i IDENTITY,  --identity IDENTITY   entityID URL of the identity provider, e.g. https://idp.admin.grnet.gr/idp/shibboleth
  -s SERVICE,   --service SERVICE     full URL of the Service Provider's authentication link the probe will test.
```
#### CLI command
```bash
sample command: checklogin -d 20 -v debug -u $USER -p $PASSWORD -s https://snf-666522.vm.okeanos.grnet.gr/ssp/module.php/core/authenticate.php?as=egi-sp
                           -i https://idp.admin.grnet.gr/idp/shibboleth

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
* AAI Proxy presents the Discovery Service and the user selects and IdP
* The user authenticates to the IdP
  * Basic authentication post
  * SAML Response post back to the proxy
  * A number of simplesamlphp modules will fire. Last will always be the consent page
* The user lands to the home page of the service

The probes return exit codes and performance data according to Nagios Plugins Specifications.

## License
Licensed under the Apache 2.0 license, for details see [LICENSE](https://github.com/ioigoume/rciam_probes/blob/master/LICENSE)