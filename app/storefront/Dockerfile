FROM python:3.14.0-slim-trixie@sha256:0aecac02dc3d4c5dbb024b753af084cafe41f5416e02193f1ce345d671ec966e

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    ORDERS_API_URL=http://orders-api:8080

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home --shell /usr/sbin/nologin app \
    && install --directory --owner=app --group=app --mode=0750 /app

WORKDIR /app
COPY --chown=app:app server.py index.html /app/

USER 10001:10001
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=2)"]

ENTRYPOINT ["python", "/app/server.py"]
