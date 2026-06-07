#!/usr/bin/env bash
set -euo pipefail

api_url="${BIG_BROTHER_API_URL:-http://127.0.0.1:8080/healthz}"
triton_url="${BIG_BROTHER_TRITON_URL:-http://127.0.0.1:8000/v2/health/ready}"

curl -fsS "$api_url"
printf '\n'
curl -fsS "$triton_url"
printf '\n'
