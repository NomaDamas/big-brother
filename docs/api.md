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

## Audit Export

```bash
curl -i http://localhost:8080/v1/audit/export \
  -H "Authorization: Bearer $BIG_BROTHER_ADMIN_TOKEN"
```

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
