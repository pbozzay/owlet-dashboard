FROM python:3.12-slim

RUN useradd --create-home --uid 1000 owlet
WORKDIR /srv/owlet

COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install --no-cache-dir .

RUN mkdir -p /data && chown owlet:owlet /data

USER owlet
VOLUME /data
ENV DATABASE_PATH=/data/owlet.sqlite3
EXPOSE 8888

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8888", \
     "--proxy-headers", "--forwarded-allow-ips=*"]
