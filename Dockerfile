FROM python:3.6.3-alpine3.6

RUN set -ex \
 && mkdir -p /app

COPY mossbot.py /app/mossbot.py
COPY Pipfile /app/Pipfile
COPY Pipfile.lock /app/Pipfile.lock

WORKDIR app/

RUN set -ex \
 && apk upgrade -a --no-cache \
 && apk add --no-cache -t .buildDeps \
        gcc \
        git \
        libjpeg-turbo-dev \
        musl-dev \
        zlib-dev \
 && apk add --no-cache \
        libjpeg-turbo \
        su-exec \
        tini \
        zlib \
 && pip install pipenv \
 && addgroup -S mossbot \
 && adduser -h /app -H -S -G mossbot -s /bin/sh mossbot \
 && chown -R mossbot:mossbot /app \
 && pipenv install --deploy --system  \
 && apk del .buildDeps

ENTRYPOINT ["/sbin/tini", "--"]
CMD ["su-exec", "mossbot", "python", "mossbot.py", "config.yml"]
