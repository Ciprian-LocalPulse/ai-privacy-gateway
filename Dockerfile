Multi-stage production-ready Dockerfile for AI Privacy Gateway
==============================================================================
Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends

build-essential

&& rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY ai_privacy_gateway/ ./ai_privacy_gateway/

Build wheels for app dependencies to accelerate installation
RUN pip install --no-cache-dir --user .

Stage 2: Final minimal runtime execution environment
FROM python:3.11-slim AS runtime

WORKDIR /app

Copy python dependencies from builder stage
COPY --from=builder /root/.local /root/.local
COPY policies/ ./policies/
COPY ai_privacy_gateway/ ./ai_privacy_gateway/

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

Starts proxy gateway stack (assumes an entrypoint runner file script wrapper exists)
CMD ["python", "-m", "ai_privacy_gateway.proxy.gateway"]
"""