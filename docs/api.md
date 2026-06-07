# API

The API is local-first and exposes the same surface used by the Docker Compose
installer.

## Health

```bash
curl -i http://localhost:8080/healthz
```

## Scan Upload

```bash
curl -i -F image=@tests/fixtures/images/known_match.bin\;type=image/jpeg \
  http://localhost:8080/v1/scan
```

Successful responses include `request_id`, `decision`, `reason`, and
`audit_event_ids`. Known synthetic matches return `decision=blocked` with
`reason=known_illegal_match`.

## Review Override

```bash
curl -i -X POST http://localhost:8080/v1/reviews/review_1/override \
  -H "Authorization: Bearer $BIG_BROTHER_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"decision":"allowed","reason":"false positive after human review"}'
```

A non-empty `reason` is required; an empty reason returns `400`
(`override_reason_required`).

> Admin token enforcement is active only when `BIG_BROTHER_DEV_MODE=false`. The
> default development configuration (`BIG_BROTHER_DEV_MODE=true`) bypasses the
> token check, so the `Authorization` header is accepted but not required. When
> enforced, send the token via `Authorization: Bearer <token>` or the
> `X-Admin-Token` header. A missing or wrong token returns `401`
> (`admin_token_required`).

## Audit Export

```bash
curl -i http://localhost:8080/v1/audit/export \
  -H "Authorization: Bearer $BIG_BROTHER_ADMIN_TOKEN"
```

The response is newline-delimited JSON (`application/x-ndjson`). Like the review
override endpoint, the admin token is enforced only when
`BIG_BROTHER_DEV_MODE=false`.

## Hash Bank Import Status

```bash
curl -i http://localhost:8080/v1/hashbank/import-status
```

Returns the number of active hash entries currently loaded (`active_entries`)
and the configured `hashbank_path`.

## Policy Validation

```bash
curl -i -X POST http://localhost:8080/v1/policy/validate \
  -H "Content-Type: application/json" \
  --data-binary @tests/fixtures/policies/default.json
```

## Integration Examples

Repository examples:

- `examples/curl/scan.sh`
- `examples/python/scan.py`
- `examples/node/scan.mjs`
- `examples/nginx/upload-hook.conf`
- `examples/discourse/webhook.rb`
