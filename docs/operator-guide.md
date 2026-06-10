# Operator Guide

The first release target is a single Linux server with an NVIDIA GPU and Docker
Compose. The API and model services stay local by default; no telemetry or
external reporting endpoint is configured.

## Prerequisites

- Supported Ubuntu LTS release.
- NVIDIA driver installed by the operator.
- NVIDIA Container Toolkit installed by the operator.
- Docker and Docker Compose.
- An operator-authorized JSONL hash bank. Do not use real illegal media or
  restricted hash sources unless you are authorized to possess and process them.

## Operating principles

- Keep the service local unless a later deployment explicitly enables remote
  integrations.
- Import only authorized hash lists.
- Mount production hash banks read-only.
- Use synthetic fixtures for tests and demos.
- Route uncertain model output to review.
- Review audit logs after every policy change.

## Production configuration

Copy the example environment file and replace every placeholder before first
start:

```bash
cp .env.example .env
mkdir -p data/hashbanks
```

Required production values:

```env
BIG_BROTHER_DEV_MODE=false
BIG_BROTHER_ADMIN_TOKEN=<long random operator secret>
BIG_BROTHER_HASHBANK_PATH=/data/hashbanks/operator-known-match.jsonl
BIG_BROTHER_AUDIT_LOG_PATH=/app/.omo/evidence/api-audit.jsonl
BIG_BROTHER_MODEL_TRIAGE_ENABLED=false
```

Place the authorized JSONL hash bank at
`data/hashbanks/operator-known-match.jsonl` on the host. Compose mounts
`./data/hashbanks:/data/hashbanks:ro`, so the API can read the file but cannot
mutate the operator's source data.

When `BIG_BROTHER_DEV_MODE=false`, startup rejects a missing or empty production hash bank, invalid hash-bank JSONL, a missing admin token, or the placeholder
admin token. This prevents silent operation against test fixtures or an empty
hash set.

## Starting locally

```bash
docker compose up -d --build
./scripts/health-check.sh
curl -i http://localhost:8080/v1/hashbank/import-status
```

The import-status response should show `active_entries` greater than zero and the
configured `hashbank_path`.

## Scan behavior

`/v1/scan` upload scanning computes SHA-256 exact matches against the active hash
bank. PDQ support is available for precomputed PDQ hash-bank and matcher
workflows, but the upload endpoint does not compute PDQ hashes from images yet.

Optional local model triage is disabled by default. To enable Hugging Face image
triage, install the optional GPU dependencies in the runtime image or host
runtime, provide a reviewed local model config, and set:

```env
BIG_BROTHER_MODEL_TRIAGE_ENABLED=true
BIG_BROTHER_MODEL_CONFIG_PATH=/path/to/model-inference.yaml
```

Model output may produce `no_action`, `review_required`, or `policy_blocked`.
Model output must not be treated as an illegality finding by itself.

## Manual QA drill

Use synthetic fixtures only:

1. Confirm `BIG_BROTHER_DEV_MODE=false` and a non-placeholder
   `BIG_BROTHER_ADMIN_TOKEN` are set.
2. Confirm `/v1/hashbank/import-status` shows the expected hash bank and active
   entries.
3. Upload a synthetic known-match image and expect `decision=blocked` with
   `reason=known_illegal_match`.
4. Upload a synthetic unknown image and expect `allowed` when model triage is
   disabled, or a review/no-action model result when enabled.
5. Call review override and audit export without a token and expect `401`.
6. Repeat with `Authorization: Bearer <token>` or `X-Admin-Token` and expect the
   operation to succeed.
7. Export audit JSONL and confirm raw image bytes are not stored.
8. Temporarily point `BIG_BROTHER_HASHBANK_PATH` at a missing file and confirm
   startup fails clearly.

## Audit and retention

Audit logs are newline-delimited JSON under `BIG_BROTHER_AUDIT_LOG_PATH`. Back up
that path according to your legal and operational retention requirements. Avoid
storing original images unless counsel and your documented retention policy
require it.
