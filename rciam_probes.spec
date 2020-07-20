# sitelib
%define dir /usr/libexec/argo-monitoring/probes/rciam

Name: rciam_probes
Summary: RCIAM related probes
Version: 1.0.5
Release: 1%{?dist}
License: Apache-2.0
Source0: %{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root
Group: Network/Monitoring
BuildArch: noarch
Requires: python-cffi,python-cryptography,python-lxml,python-pycparser,python-pyOpenSSL,python-six,python-urllib3,python-xmltodict,python-selinium,python-beautifulsoup4

%description
This package includes probes for RCIAM.
Currently it supports the following components:
 - Metadata Health
 - Login Health

%prep
%setup -q

%build
%{__python3} setup.py build

%install
rm -rf %{buildroot}
%{__python3} setup.py install --skip-build --root %{buildroot} --record=INSTALLED_FILES
install -d -m 755 %{buildroot}/%{dir}
install -d -m 755 %{buildroot}/%{python3_sitelib}/rciam_probes

%clean
rm -rf %{buildroot}

%files -f INSTALLED_FILES
%defattr(-,root,root,0755)
%{python3_sitelib}/rciam_probes
%{dir}


%changelog
* Mon Jul 20 2020 Ioannis Igoumenos <ioigoume@admin.grnet.gr> 1.0.5
- Fixed wrong url evaluation of Service landing page
