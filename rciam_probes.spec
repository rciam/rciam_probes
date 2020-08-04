%{!?python_sitelib: %global python_sitelib %(%{__python3} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
# sitelib
%define _unpackaged_files_terminate_build 0
%define _binaries_in_noarch_packages_terminate_build 0
%define argo_path argo-monitoring/probes

Name: rciam_probes
Summary: RCIAM related probes
Version: 1.0.5
# fixme: macro could not be resolved
Release: 1%{?dist}
Url: https://github.com/rciam/%{name}
License: Apache-2.0
Vendor: GRNET SA
Source0: %{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root
Group: Network/Monitoring
BuildArch: noarch
Requires: python36-cffi
Requires: python36-cryptography
Requires: python36-lxml
Requires: python36-pycparser
Requires: python36-pyOpenSSL
Requires: python36-six
Requires: python36-urllib3
Requires: python36-xmltodict
Requires: python36-beautifulsoup4
Requires: python36-requests
Requires: firefox-68
#Requires: python36-selenium # This is not supported for Centos7


%description
This package includes probes for RCIAM.
Currently it supports the following components:
 - Metadata Health
 - Login Health

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
# documentation
%doc README.md CHANGELOG.md
%license LICENSE

%changelog
* Mon Jul 20 2020 Ioannis Igoumenos <ioigoume@admin.grnet.gr> 1.0.5
- Restructured package
- Fixed non existing log file after setup.py install
- Add geckodriver into configuration list
- Fixed python packaging
- Tested with python version 3.6
- Updated README.md
* Thu Jun 11 2020 Ioannis Igoumenos <ioigoume@admin.grnet.gr> 1.0.4
- Fixed wrong url evaluation of Service landing page
* Fri May 29 2020 Ioannis Igoumenos <ioigoume@admin.grnet.gr> 1.0.1
- Initial version of the package