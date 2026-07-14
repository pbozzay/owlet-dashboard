FROM python:3.12-slim

# gosu lets the entrypoint drop from root to the runtime user cleanly.
RUN apt-get update \
 && apt-get install -y --no-install-recommends gosu \
 && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 owlet
WORKDIR /srv/owlet

COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install --no-cache-dir .

COPY docker-entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

RUN mkdir -p /data && chown owlet:owlet /data

VOLUME /data
ENV DATABASE_PATH=/data/owlet.sqlite3
# Override to match your host share owner (Unraid appdata is usually 99:100).
ENV PUID=1000 PGID=1000
EXPOSE 8888

# Entrypoint starts as root only to fix /data ownership, then execs uvicorn as
# PUID:PGID. Do not add `USER` here — that would defeat the ownership fixup.
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8888", \
     "--proxy-headers", "--forwarded-allow-ips=*"]
