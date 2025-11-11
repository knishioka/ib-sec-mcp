#!/bin/bash
set -euo pipefail

# Only run in Claude Code on the web
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  echo "Skipping session start hook (not in remote environment)"
  exit 0
fi

echo "=== IB Analytics Session Start ==="
echo "Installing dependencies..."

# Use Python 3.12 explicitly (required by project)
# Install all dependencies including dev tools
# Using --break-system-packages is safe in containerized web environment
# Using -q for quieter output to reduce noise
python3.12 -m pip install -q --break-system-packages -e ".[dev,mcp,visualization,reporting]"

# Set PYTHONPATH for the session to enable imports
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo 'export PYTHONPATH="$CLAUDE_PROJECT_DIR:$PYTHONPATH"' >> "$CLAUDE_ENV_FILE"
fi

echo "✅ Dependencies installed successfully"
echo "✅ Development tools ready: pytest, ruff, mypy"
echo "✅ Session environment configured"
echo ""
