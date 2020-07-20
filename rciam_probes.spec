%{!?python_sitelib: %global python_sitelib %(%{__python3} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
# sitelib
%define dir /usr/libexec/argo-monitoring/probes/rciam_probes

Name: rciam_probes
Summary: RCIAM related probes
Version: 1.0.5
Release: 1%{?dist}
License: Apache-2.0
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
Requires: python3-selinium
Requires: python3-beautifulsoup4

%description
This package includes probes for RCIAM.
Currently it supports the following components:
 - Metadata Health
 - Login Health

%prep
%setup -q

%build
python3 setup.py build

%install
rm -rf %{buildroot}
python3 setup.py install --skip-build --root %{buildroot} --record=INSTALLED_FILES
install -d -m 755 %{buildroot}/%{dir}
install -d -m 755 %{buildroot}/%{python_sitelib}/rciam_probes

%clean
rm -rf %{buildroot}

%files -f INSTALLED_FILES
%defattr(-,root,root,0755)
%{python_sitelib}/rciam_probes
%{dir}


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