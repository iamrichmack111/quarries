FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    QUARRIES_HOST=0.0.0.0 \
    QUARRIES_PORT=8787

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        pkg-config \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY . /app

RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel \
    && python -m pip install --no-cache-dir .

RUN useradd --create-home --uid 10001 quarries \
    && mkdir -p /home/quarries/.local/share/quarries \
    && chown -R quarries:quarries /app /home/quarries

USER quarries

EXPOSE 8787

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8787/api/status || exit 1

CMD ["python", "-m", "quarries.webapp"]
