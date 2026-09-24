# bookworm (Debian 12) pinned deliberately: Reclaim Cloud / Virtuozzo runs custom
# containers as system containers and rejects base images newer than it knows.
FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DATABASE_URL=sqlite:////data/aggrssive.db LTI_KEY_PATH=/data/lti_private_key.pem

WORKDIR /app
COPY pyproject.toml README.md ./
COPY aggrssive ./aggrssive
RUN pip install --no-cache-dir . && mkdir -p /data

VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=60s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/')" || exit 1

CMD ["uvicorn", "aggrssive.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
