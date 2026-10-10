#!/usr/bin/env bash
# Create .env with freshly generated secrets (idempotent: never overwrites).
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ -f .env ]]; then
  echo ".env already exists - leaving it untouched."
  exit 0
fi

rand() { openssl rand -hex 32; }

cp .env.example .env
sed -i "s|^TOOL_API_KEY=.*|TOOL_API_KEY=$(rand)|" .env
sed -i "s|^WEBUI_SECRET_KEY=.*|WEBUI_SECRET_KEY=$(rand)|" .env
chmod 600 .env

echo "Wrote .env with generated secrets (mode 600)."
