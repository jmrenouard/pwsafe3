FROM fedora:latest
RUN mkdir /data
WORKDIR /data
RUN yum -y install perl-Data-Dumper perl-Crypt-PWSafe3
ENTRYPOINT [ "perl", "/data/convert" ]