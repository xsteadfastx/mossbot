FROM python:alpine

COPY . /opt/mossbot

WORKDIR /opt/mossbot

RUN set -ex \
 && apk add --no-cache \
        git \
        su-exec \
        tini \
 && pip install pipenv \
 && addgroup -S mossbot \
 && adduser -h /opt/mossbot -H -S -G mossbot -s /bin/sh mossbot \
 && chown -R mossbot:mossbot /opt/mossbot \
 && su mossbot -c "pipenv install --three"

ENTRYPOINT ["/sbin/tini", "--"]
CMD ["su-exec", "mossbot", "pipenv", "run", "python", "mossbot.py", "config.yml"]

