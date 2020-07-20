from string import Template

"""Nagios template output for Login health check"""
login_health_check_tmpl = Template("SP Login succeeded(${time}sec time) | 'Login'=${time}s")

defaults_login_health_check = {
    "time": -1
}

"""Nagios template output for Cert health check"""
cert_health_check_tmpl = Template("SSL_CERT(${type}) ${status} - x509 certificate '${subject}' from '${issuer}' is valid until "
                                  "${not_after} (expires in ${expiration_days} days) | 'SSL Metadata Cert'=${"
                                  "expiration_days};${warning};${critical};0;3650")

defaults_cert_health_check = {
    "type": "",
    "status": "",
    "subject": "",
    "issuer": "",
    "not_after": "",
    "expiration_days": "",
    "warning": "",
    "critical": "",
}

"""Nagios template output for Cert health check - Type all"""
cert_health_check_all_tmpl = Template("SSL_CERT(${type}) ${status}")

defaults_cert_health_check_all = {
    "type": "",
    "status": ""
}