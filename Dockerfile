# Python minor pinned; resolve the desired patch/digest in your deployment policy.
FROM python:3.12-slim-bookworm AS runtime
ARG SOURCE_URL=https://github.com/wkarts/ARGWS-Reseller-Manager
ARG SOURCE_REVISION=unknown
LABEL org.opencontainers.image.source="${SOURCE_URL}" \
      org.opencontainers.image.revision="${SOURCE_REVISION}" \
      org.opencontainers.image.title="Reseller Manager" \
      org.opencontainers.image.description="FastAPI reseller bridge with verified contracts" \
      org.opencontainers.image.version="0.1.3"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    RESMAN_DATA=/data RESMAN_HOST=0.0.0.0 RESMAN_PORT=48190 HOME=/data \
    PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers RESMAN_BROWSER_HEADLESS=1
WORKDIR /app
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --only-binary=:all: -r requirements.txt \
    && python -m playwright install --with-deps chromium \
    && chmod -R a+rX /opt/pw-browsers \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -g 10001 reseller \
    && useradd -u 10001 -g 10001 -d /data -s /usr/sbin/nologin reseller \
    && mkdir /data && chown 10001:10001 /data && chmod 700 /data
COPY app/ app/
COPY scripts/init_data.py scripts/init_data.py
COPY VERSION ./
USER 10001:10001
EXPOSE 48190
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; r=urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://127.0.0.1:48190/health',timeout=3); assert r.status==200"
ENTRYPOINT ["python", "-m", "app.runtime"]

# Compatibility target: standard runtime already includes Playwright and Chromium.
FROM runtime AS browser
