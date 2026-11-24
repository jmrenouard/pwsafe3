FROM fedora:41

RUN dnf -y install perl-Data-Dumper perl-Crypt-PWSafe3 \
    && dnf clean all \
    && rm -rf /var/cache/dnf \
    && useradd -r -u 10001 -m app \
    && mkdir -p /data \
    && chown app:app /data

WORKDIR /data
COPY --chown=app:app convert.pl /usr/local/bin/convert.pl
USER app

ENTRYPOINT ["perl", "/usr/local/bin/convert.pl"]
