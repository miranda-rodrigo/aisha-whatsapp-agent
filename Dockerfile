FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg curl unzip \
    && curl -fsSL https://deno.land/install.sh | sh \
    && rm -rf /var/lib/apt/lists/*
ENV DENO_INSTALL=/root/.deno
ENV PATH=/root/.deno/bin:$PATH
WORKDIR /app
COPY packages/chat-analysis /app/packages/chat-analysis
COPY apps/agent /app/apps/agent
RUN pip install --no-cache-dir /app/packages/chat-analysis /app/apps/agent
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright
RUN python -m playwright install --with-deps chromium
# Explicit copy list: no local data, website, launcher or playground in production.
COPY scripts /app/scripts
CMD uvicorn aisha.app:app --host 0.0.0.0 --port ${PORT:-8000}
