# Multi-stage build for IB Analytics MCP Server
# Based on Docker MCP Server best practices (2025)

# Stage 1: Builder
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY pyproject.toml ./

# Install dependencies to /install
RUN pip install --no-cache-dir --prefix=/install .

# Stage 2: Runtime
FROM python:3.12-slim

LABEL org.opencontainers.image.title="IB Analytics MCP Server"
LABEL org.opencontainers.image.description="Interactive Brokers Portfolio Analytics with MCP"
LABEL org.opencontainers.image.version="0.1.0"
LABEL org.opencontainers.image.authors="Kenichiro Nishioka"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY ib_sec_mcp ./ib_sec_mcp
COPY pyproject.toml ./

# Install the package
RUN pip install --no-cache-dir -e ".[mcp]"

# Create data directories
RUN mkdir -p data/raw data/processed && \
    chmod 755 data

# Security: Run as non-root user
RUN useradd -m -u 1000 mcpuser && \
    chown -R mcpuser:mcpuser /app
USER mcpuser

# Environment variables (override with docker run -e)
ENV PYTHONUNBUFFERED=1 \
    IB_DEBUG=0

# Health check (optional, for HTTP transport)
# HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
#   CMD python -c "import sys; sys.exit(0)"

# Default command: run MCP server
CMD ["ib-sec-mcp"]
