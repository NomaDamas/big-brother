#!/usr/bin/env bash
set -euo pipefail

port="${BIG_BROTHER_DEMO_PORT:-18080}"
base_url="http://127.0.0.1:${port}"
session_dir=".omo/demo"
server_log=".omo/evidence/task-13-demo-server.log"
server_pid=""

cleanup() {
  if [[ -n "$server_pid" ]] && kill -0 "$server_pid" >/dev/null 2>&1; then
    kill "$server_pid" >/dev/null 2>&1 || true
    wait "$server_pid" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT

mkdir -p .omo/evidence
rm -rf "$session_dir"
uv run uvicorn big_brother.api.app:create_default_app --factory --host 127.0.0.1 --port "$port" >"$server_log" 2>&1 &
server_pid="$!"

for _ in 1 2 3 4 5 6 7 8 9 10; do
  if curl -fsS "${base_url}/healthz" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

uv run big-brother demo seed --output-dir "$session_dir"
scan_response="$(curl -fsS -F "image=@${session_dir}/known_match.jpg;type=image/jpeg" "${base_url}/v1/scan")"
model_response="$(uv run big-brother decision model-signal --category explicit --score 0.91)"

case "$scan_response" in
  *'"decision":"blocked"'*)
    printf 'known_match=blocked\n'
    ;;
  *)
    printf 'known_match=failed\n' >&2
    exit 1
    ;;
esac

case "$model_response" in
  *'decision=review_required'*)
    printf 'model_signal=review_required\n'
    ;;
  *)
    printf 'model_signal=failed\n' >&2
    exit 1
    ;;
esac

printf 'PASS\n'
