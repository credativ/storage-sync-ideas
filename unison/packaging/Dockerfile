FROM rockylinux:8

RUN yum install -y rpmdevtools rpmlint yum-utils make which texlive
RUN yum-config-manager --enable powertools
RUN yum install -y ocaml
RUN useradd build -d /build
USER build
WORKDIR /build
RUN rpmdev-setuptree
COPY unison.spec rpmbuild/SPECS/
RUN spectool -g -R rpmbuild/SPECS/unison.spec
RUN rpmbuild -ba rpmbuild/SPECS/unison.spec
