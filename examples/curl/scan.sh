#!/usr/bin/env bash
set -euo pipefail

api_url="${BIG_BROTHER_API_URL:-http://localhost:8080/v1/scan}"
image_path="${1:-tests/fixtures/images/known_match.bin}"

curl -i -F "image=@${image_path};type=image/jpeg" "$api_url"
