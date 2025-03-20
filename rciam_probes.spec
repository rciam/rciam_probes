%{!?python_sitelib: %global python_sitelib %(%{__python3} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
# sitelib
%define _unpackaged_files_terminate_build 0
%define _binaries_in_noarch_packages_terminate_build 0
%define argo_path argo-monitoring/probes
%define logrotate_dir logrotate.d

Name: rciam_probes
Summary: RCIAM related probes - Complete
Group: grnet/rciam
Version: 2.4.1
Release: %(echo $GIT_COMMIT_DATE).%(echo $GIT_COMMIT_HASH)%{?dist}
Url: https://github.com/rciam/%{name}
License: Apache-2.0
Vendor: GRNET SA
Source0: %{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root
Group: Network/Monitoring
BuildArch: noarch
Requires: python3-cffi
Requires: python3-cryptography
Requires: python3-lxml
Requires: python3-pycparser
Requires: python3-pyOpenSSL
Requires: python3-six
Requires: python3-urllib3
Requires: python3-xmltodict
Requires: python3-beautifulsoup4
Requires: python3-requests
Requires: python3-setuptools
Requires: logrotate
Requires: firefox
Requires: python3-selenium

%description
This package includes probes for RCIAM.
Currently it supports the following components:
 - Metadata Health
 - Login Health

%package consumer
Summary: RCIAM probes - Checkmetadata, Checklogin Consumer
Group: grnet/rciam
Requires: python3-cffi
Requires: python3-cryptography
Requires: python3-lxml
Requires: python3-pycparser
Requires: python3-pyOpenSSL
Requires: python3-six
Requires: python3-urllib3
Requires: python3-xmltodict
Requires: python3-beautifulsoup4
Requires: python3-requests
Requires: python3-setuptools
Requires: logrotate

%description consumer
This package includes probes for RCIAM.
Currently it supports the following components:
 - Metadata Health
 - Login Health - Consumer only

%prep
%setup -n %{name}-%{version}

%build
python3 setup.py build

%install
python3 setup.py install --skip-build --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES
# Copy the executables in the correct path
install --directory -m 755 %{buildroot}%{_libexecdir}/%{argo_path}/%{name}
cp bin/* %{buildroot}%{_libexecdir}/%{argo_path}/%{name}
# Copy my driver into the build
install --directory -m 755 %{buildroot}%{_includedir}/%{name}/driver
cp driver/geckodriver %{buildroot}%{_includedir}/%{name}/driver
# Create the log directory
install --directory -m 755 %{buildroot}%{_localstatedir}/log/%{name}
# Copy the log rotate configuration
install --directory -m 755 %{buildroot}%{_sysconfdir}/%{logrotate_dir}/
cp -r extras/%{logrotate_dir}/ %{buildroot}%{_sysconfdir}

%clean
rm -rf $RPM_BUILD_ROOT

%files -f INSTALLED_FILES
%defattr(-,root,root,0755)
# binaries
%dir %{_libexecdir}/%{argo_path}/%{name}
%attr(0755,root,root) %{_libexecdir}/%{argo_path}/%{name}/*
# driver
%attr(0755,root,root) %dir %{_includedir}/%{name}/driver/
%attr(0755,root,root) %{_includedir}/%{name}/driver/geckodriver
# logs
%attr(0744,nagios,nagios) %dir %{_localstatedir}/log/%{name}/
# own the log file but do not install it
%ghost %{_localstatedir}/log/%{name}/rciam_probes.log
# logrotate
%attr(0755,root,root) %dir %{_sysconfdir}/%{logrotate_dir}/
%attr(0644,root,root) %{_sysconfdir}/%{logrotate_dir}/%{name}
# documentation
%doc README.md
%license LICENSE

%files consumer -f INSTALLED_FILES
%defattr(-,root,root,0755)
# binaries
%dir %{_libexecdir}/%{argo_path}/%{name}
%attr(0755,root,root) %{_libexecdir}/%{argo_path}/%{name}/*
# logs
%attr(0744,nagios,nagios) %dir %{_localstatedir}/log/%{name}/
# own the log file but do not install it
%ghost %{_localstatedir}/log/%{name}/rciam_probes.log
# logrotate
%attr(0755,root,root) %dir %{_sysconfdir}/%{logrotate_dir}/
%attr(0644,root,root) %{_sysconfdir}/%{logrotate_dir}/%{name}
# documentation
%doc README.md
%license LICENSE

#%post
#if [ $1 == 1 ];then
#  {
#    echo '/var/log/rciam_probes/rciam_probes.log {'
#    echo '  size 100M'
#    echo '  daily'
#    echo '  missinggok'
#    echo '  notifempty'
#    echo '  compress'
#    echo '  maxage 10'
#    echo '  create'
#    echo '  rotate 10'
#    echo '}'
#  } > %{_sysconfdir}/%{logrotate_dir}/%{name}
#fi

%changelog
* Thu Mar 20 2025 Nicolas Liampotis <nliam@grnet.gr> 2.4.1
- Fixed support for IdP Discovery pages based on Keycloak in login checks
* Mon Mar 3 2025 Nicolas Liampotis <nliam@grnet.gr> 2.4.0
- Added support for IdP Discovery pages based on Keycloak in login checks
* Wed Sep 3 2024 Nicolas Liampotis <nliam@grnet.gr> 2.3.0
- Added support for IdP Discovery pages based on thiss.io in login checks
* Wed Aug 7 2024 Nicolas Liampotis <nliam@grnet.gr> 2.2.0
- Added support for varying XML namespace prefixes in SAML metadata health checks
- Added support for skipping the IdP Discovery page during login checks
* Mon Aug 5 2024 Nicolas Liampotis <nliam@grnet.gr> 2.1.1
- Fixed Python requirements. See https://github.com/seleniumbase/SeleniumBase/issues/2782
- Updated geckodriver to v0.34.0
* Wed Jul 3 2024 Nicolas Liampotis <nliam@grnet.gr> 2.1.0
- Added Python requirements
* Wed May 29 2024 Nicolas Liampotis <nliam@grnet.gr> 2.0.0
- Changed Python requirements from python36-* to python3-*
- Updated spec file for compatibility with Rocky Linux 9
* Wed Dec 7 2022 Ioannis Igoumenos <ioigoume@admin.grnet.gr> 1.2.14
- Add support for Shibboleth IdP v4 consent page
* Mon Dec 13 2021 Ioannis Igoumenos <ioigoume@admin.grnet.gr> 1.2.13
- Discovery service timeout needs to be treated as critical
- Handle non privileged file write
* Sun Dec 12 2021 Ioannis Igoumenos <ioigoume@admin.grnet.gr> 1.2.12
- Convert posixpath object to string when logging
- Convert Errors to string when logging
- Make timeout for IdP and OIDC consent views configurable
* Thu Dec 07 2021 Ioannis Igoumenos <ioigoume@admin.grnet.gr> 1.2.11
- Evaluate HTTP status code when calculating nagios status
* Thu Sep 22 2021 Ioannis Igoumenos <ioigoume@admin.grnet.gr> 1.2.10
- Do not timeout if cookie banner is not available
* Thu Sep 16 2021 Ioannis Igoumenos <ioigoume@admin.grnet.gr> 1.2.9
- Add support for OIDC server consent page
* Wed May 19 2021 Ioannis Igoumenos <ioigoume@admin.grnet.gr> 1.2.8
- Improve Exception handling
* Mon Apr 12 2021 Ioannis Igoumenos <ioigoume@admin.grnet.gr> 1.2.7
- Support evaluation of multiple json entries
* Tue Feb 2 2021 Ioannis Igoumenos <ioigoume@admin.grnet.gr> 1.2.6
- Improve logging
- Fix Selenium Import for consumer package
* Tue Jan 26 2021 Ioannis Igoumenos <ioigoume@admin.grnet.gr> 1.2.5
- Fix cases where we do not use the default loader class
* Fri Jan 22 2021 Ioannis Igoumenos <ioigoume@admin.grnet.gr> 1.2.3
- Exclude selenium and firefox packages for `slim` version
* Mon Jan 04 2021 Ioannis Igoumenos <ioigoume@admin.grnet.gr> 1.2.2
- Fixed debug messages and undefined var in stale status
* Mon Dec 21 2020 Ioannis Igoumenos <ioigoume@admin.grnet.gr> 1.2.1
- Changed only the configuration [--json]. It now supports custom output paths.
* Fri Dec 11 2020 Ioannis Igoumenos <ioigoume@admin.grnet.gr> 1.2.0
- Added configuration [-J|--json], export output in json format.
- Added configuration [-e|--inlocation], import monitoring data from external source
* Tue Oct 27 2020 Ioannis Igoumenos <ioigoume@admin.grnet.gr> 1.1.3
- changed webdriver.(Reverted)Firefox log path attribute from `service_log_path` to deprecated `log_path`
* Mon Oct 26 2020 Ioannis Igoumenos <ioigoume@admin.grnet.gr> 1.1.2
- changed webdriver.Firefox log path attribute from deprecated `log_path` to `service_log_path`
- redirect Geckodriver's logs to dev/null if on -C(console) mode
* Tue Oct 20 2020 Ioannis Igoumenos <ioigoume@admin.grnet.gr> 1.1.1
- rciam_probes.spec fixed
* Mon Oct 19 2020 Ioannis Igoumenos <ioigoume@admin.grnet.gr> 1.1.0
- Changed verbosity notation. Default is critical. -v error, -vv warning, -vvv info, -vvvv debug
- Enabled logging output both into a file or into stdout
- Added Service Provider landing page into configuration list. Optional parameter
- Added Logrotate support
- Restructured package
- Fixed log directory and file initialization
- Add geckodriver into configuration list. Optional parameter
- Fixed python packaging
- Tested with python version 3.6
- Updated README.md
* Thu Jun 11 2020 Ioannis Igoumenos <ioigoume@admin.grnet.gr> 1.0.4
- Fixed wrong url evaluation of Service landing page
* Fri May 29 2020 Ioannis Igoumenos <ioigoume@admin.grnet.gr> 1.0.1
- Initial version of the package
