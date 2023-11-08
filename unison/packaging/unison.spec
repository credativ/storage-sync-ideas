Name:           unison
Version:        2.53.3
Release:        1%{?dist}
Summary:        Unison is a file-synchronization tool for POSIX-compliant systems

License:        GPLv3
URL:            https://github.com/bcpierce00/unison/
Source0:        https://github.com/bcpierce00/unison/archive/refs/tags/v%{version}.tar.gz

BuildRequires:  ocaml texlive

%description


%prep
%autosetup


%build
make all docs

%install
rm -rf $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT/%{_bindir}
mkdir -p $RPM_BUILD_ROOT/%{_docdir}/unison
mkdir -p $RPM_BUILD_ROOT/%{_mandir}/man1
cp %{_builddir}/%{name}-%{version}/src/unison $RPM_BUILD_ROOT/%{_bindir}
cp %{_builddir}/%{name}-%{version}/src/unison-fsmonitor $RPM_BUILD_ROOT/%{_bindir}
cp %{_builddir}/%{name}-%{version}/doc/unison-manual.pdf $RPM_BUILD_ROOT/%{_docdir}/unison
cp %{_builddir}/%{name}-%{version}/man/unison.1 $RPM_BUILD_ROOT/%{_mandir}/man1
gzip $RPM_BUILD_ROOT/%{_mandir}/man1/unison.1


%files
%{_bindir}/*
%{_mandir}/*
%{_docdir}/*

%clean
rm -rf %{buildroot} %{_builddir}
