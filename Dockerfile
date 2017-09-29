FROM python:alpine

COPY . /opt/mossbot

WORKDIR /opt/mossbot

RUN set -ex \
 && apk upgrade -a --no-cache \
 && apk add --no-cache -t .buildDeps \
        gcc \
        git \
        libjpeg-turbo-dev \
        musl-dev \
        zlib-dev \
 && apk add --no-cache \
        su-exec \
        tini \
 && pip install pipenv \
 && addgroup -S mossbot \
 && adduser -h /opt/mossbot -H -S -G mossbot -s /bin/sh mossbot \
 && chown -R mossbot:mossbot /opt/mossbot \
 && su mossbot -c "pipenv install --three" \
 && apk del .buildDeps

ENTRYPOINT ["/sbin/tini", "--"]
CMD ["su-exec", "mossbot", "pipenv", "run", "python", "mossbot.py", "config.yml"]
