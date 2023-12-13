FROM rockylinux:9 AS ocaml-src

RUN yum install -y yum-utils
RUN yum-config-manager --enable crb
WORKDIR /
RUN yumdownloader --source ocaml

FROM rockylinux:8 AS ocaml-bin

RUN yum install -y rpmdevtools rpmlint yum-utils
COPY --from=ocaml-src /ocaml-4.11.1-5.el9.2.src.rpm /tmp/
RUN yum-builddep -y /tmp/ocaml-4.11.1-5.el9.2.src.rpm
RUN rpmbuild --rebuild /tmp/ocaml-4.11.1-5.el9.2.src.rpm

FROM rockylinux:8

RUN yum install -y rpmdevtools yum-utils

RUN useradd build -d /build
USER build
WORKDIR /build
RUN rpmdev-setuptree
COPY unison.spec rpmbuild/SPECS/
RUN spectool -g -R rpmbuild/SPECS/unison.spec

USER root
COPY --from=ocaml-bin /root/rpmbuild/RPMS/x86_64/*.rpm rpmbuild/RPMS/
RUN yum install -y rpmbuild/RPMS/ocaml-4.11.1-5.el8.2.x86_64.rpm rpmbuild/RPMS/ocaml-runtime-4.11.1-5.el8.2.x86_64.rpm rpmbuild/RPMS/ocaml-compiler-libs-4.11.1-5.el8.2.x86_64.rpm
RUN yum-builddep -y rpmbuild/SPECS/unison.spec

USER build
RUN rpmbuild -ba rpmbuild/SPECS/unison.spec
