%define name python-GridMon
%define version 1.1.13
%define release 1%{?dist}
%define etcdir /etc/gridmon
%define probes_workdir /var/lib/gridprobes

Summary: Helper package for python grid-monitoring applications
Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{name}-%{version}.tar.gz
License: ASL 2.0
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-buildroot
Prefix: %{_prefix}
BuildArchitectures: noarch
Vendor: James Casey <james.casey@cern.ch>
Url: http://cern.ch/

%description
A python helper library for EGEE OAT grid monitoring tools.
It contains helper routines for Nagios and Grid Security


%prep
%setup

%build
CFLAGS="$RPM_OPT_FLAGS" %{__python} setup.py build

%install
rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install --skip-build --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES
sed -i "s+^"%{etcdir}".*++" INSTALLED_FILES

%post
if [ -d /var/run/gridprobes ] && [ ! -d %{probes_workdir} ] ; then
    mv /var/run/gridprobes %{probes_workdir}
fi
if [ "$1" = "1" ] ; then  # first install
    mkdir -p %{probes_workdir}
    chmod 1777 %{probes_workdir}
    chown 0:0 %{probes_workdir}
fi

%postun
if [ "$1" = "0" ] ; then # last uninstall
    %{__rm} -rf %{probes_workdir}
fi

%clean
rm -rf $RPM_BUILD_ROOT

%files -f INSTALLED_FILES
%defattr(-,root,root)
%config(noreplace) %{etcdir}/gridmon.conf
%config(noreplace) %{etcdir}/gridmon.errdb
%config(noreplace) /etc/nagios-submit.conf
%doc CHANGES

%changelog
* Fri Jun 30 2017 Marian Babik <Marian.Babik@cernc.h> - 1.1.15-1
- Added an explicit flush to cmd pipe
* Fri Nov 06 2015 Marian Babik <Marian.Babik@cernc.h> - 1.1.14-1
- Removing equals sign from probe var directory
* Mon Jan 14 2013 Marian Babik <Marian.Babik@cern.ch> - 1.1.13-1
- SAM-3091 Added nagios-submit configuration file 
* Thu Nov 18 2010 K. Skaburskas <Konstantin.Skaburskas@cern.ch> - 1.1.12-1
- bugfix
* Tue Jun 1 2010 K. Skaburskas <Konstantin.Skaburskas@cern.ch> - 1.1.8-6
- SAM-503: creation/deletion of probes working directory moved here from
  grid-monitoring-probes-org.sam RPM
