FROM python:3.11-slim

# Faster, cleaner Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (SSL certs, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App
COPY alfresco_mcp_server.py .

# Defaults (can be overridden by compose/env)
ENV ALFRESCO_HOST=http://localhost:8080
ENV TRANSPORT_MODE=stdio
ENV PORT=8000

EXPOSE ${PORT:-8000}

# POSIX shell (slim may not have bash)
RUN printf '%s\n' \
  '#!/bin/sh' \
  'set -eu' \
  'case "${TRANSPORT_MODE:-http}" in' \
  '  http)' \
  '    echo "Starting in HTTP mode on port ${PORT:-8000}"' \
  '    exec python alfresco_mcp_server.py --transport http --host 0.0.0.0 --port "${PORT:-8000}"' \
  '    ;;' \
  '  sse)' \
  '    echo "Starting in SSE mode on port ${PORT:-8000}"' \
  '    exec python alfresco_mcp_server.py --transport sse --host 0.0.0.0 --port "${PORT:-8000}"' \
  '    ;;' \
  '  stdio|*)' \
  '    echo "Starting in STDIO mode"' \
  '    exec python alfresco_mcp_server.py --transport stdio' \
  '    ;;' \
  'esac' > /entrypoint.sh \
  && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
