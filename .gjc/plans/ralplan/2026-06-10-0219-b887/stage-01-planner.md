# RALPLAN-DR short-mode plan: readiness gaps

## Summary
Plan immediate ultragoal execution for four readiness gaps in `big-brother`: production hashbank loading, PDQ upload scope, optional model triage scope/integration, and production deploy/operator hardening. Repo inspection found `src/big_brother/api/app.py` production default loads `tests/fixtures/hashbanks/known-match.jsonl`; `Dockerfile` copies fixture hashbanks; `docker-compose.yml` has no operator hashbank mount/env; `/v1/scan` runs SHA-256 only via `KnownContentMatcher.scan()` while PDQ exists only as `scan_pdq()`; model clients and `DecisionEngine` exist but are not invoked by `/v1/scan`; operator docs are skeletal.

## Principles
1. No test fixture defaults in production runtime paths.
2. Public docs must match observable `/v1/scan` behavior.
3. Local-first/no-telemetry remains invariant; operator-owned hashbanks and models only.
4. Fail safely and explicitly on invalid production config; never silently scan empty/fixture data.
5. Model output may route to review/no_action, never legal-illegal finding by itself.

## Top decision drivers
1. Compliance risk from fixture or empty production hashbank.
2. Operator usability through Docker Compose and explicit env/volumes.
3. Scope honesty for PDQ/model claims before push to `main`.

## Options
### Option A: hashbank hardening plus truthful docs only
Pros: lowest risk; removes dangerous fixture default quickly; avoids fake PDQ/model wiring. Cons: weakens README value proposition; upload endpoint remains hash-only; requires clear release limitation.

### Option B: hashbank hardening plus optional model triage, truthful PDQ upload correction
Pros: uses existing `models/*`, `decision/engine.py`, and policy types; aligns optional triage claim without fake stubs; preserves known-match precedence. Cons: adds runtime config/dependency handling; needs careful tests; model QA is optional/local.

### Option C: hashbank hardening plus PDQ upload plus model triage
Pros: best feature alignment. Cons: no inspected image-to-PDQ computation path/dependency; larger license/normalization risk; too broad for immediate compliance hardening.

## Chosen recommendation and invalidation
Choose Option B. Invalidate Option A because model triage is feasible from existing code and the contract prefers implementation over doc weakening where feasible. Invalidate Option C because PDQ upload hashing is not present; implementing it safely requires dependency/license/image-normalization decisions outside immediate readiness. PDQ must be documented as matcher/hashbank support unless genuine tested image-to-PDQ computation is added.

## In scope
Production hashbank env/config loading; Docker/Compose removal of fixture defaults; optional local model triage in `/v1/scan` if concrete integration remains safe; truthful PDQ upload scope correction; README/API/operator/release docs hardening; TDD, manual QA, commit, and push after verification.

## Out of scope
Real illegal media, restricted hash lists, bundled non-redistributable models, external reporting/telemetry, legal advice, HA/Kubernetes, full PDQ image hashing unless an approved existing path is proven during execution.

## File-level execution plan
- `src/big_brother/api/app.py`: add env-backed `BIG_BROTHER_HASHBANK_PATH`, `BIG_BROTHER_AUDIT_LOG_PATH`, `BIG_BROTHER_MAX_UPLOAD_BYTES`, optional `BIG_BROTHER_MODEL_TRIAGE_ENABLED`, `BIG_BROTHER_MODEL_CONFIG_PATH`, and backend setting. Replace fixture default in `create_default_app()`. Production mode (`BIG_BROTHER_DEV_MODE=false`) must fail explicitly on missing/invalid configured hashbank. Preserve test injection through `ApiSettings(hash_entries=...)`. Orchestrate scan as upload validation -> known SHA match -> optional model triage -> final decision through `DecisionEngine`. Keep audit image-free and distinguish match/model/no-action outcomes.
- `src/big_brother/matching/engine.py`: keep SHA `scan()` behavior unless actual PDQ image hashing is implemented. Do not imply PDQ upload scan.
- `src/big_brother/models/*`: reuse `load_moderation_config()`, `TransformersImageModerationClient`, or existing Triton adapter. Add only a small factory if needed; no fake production client/stub.
- `Dockerfile`: remove `COPY tests/fixtures/hashbanks ./tests/fixtures/hashbanks`.
- `docker-compose.yml`: mount operator hashbank read-only, e.g. `./data/hashbanks:/data/hashbanks:ro`, set `BIG_BROTHER_HASHBANK_PATH`, keep audit volume, keep Triton local, document model triage disabled unless enabled.
- `.env.example`: add hashbank path, audit path, max upload bytes, model flags/config placeholders, no secrets beyond placeholders.
- `tests/api/test_scan_endpoint.py`: add production hashbank loading, missing production hashbank failure, import-status path/count, model triage review/no_action, known-match precedence, existing non-image/max-size coverage.
- `tests/install/test_compose.py`: assert hashbank env and read-only mount; add Dockerfile fixture-copy assertion if absent.
- `tests/docs/*`: assert README/API docs truthfully limit PDQ upload behavior and operator guide covers production safety items.
- `README.md`, `docs/api.md`, `docs/operator-guide.md`, `docs/release-checklist.md`: align claims, add deployment/operator hardening.

## TDD sequence
1. Write failing API tests for env hashbank load, production missing/invalid hashbank failure, and import-status count/path.
2. Implement settings/hashbank loader changes.
3. Write failing Dockerfile/Compose tests for no fixture copy plus read-only operator hashbank mount/env.
4. Implement Dockerfile/Compose/.env changes.
5. Write failing scan endpoint tests with injected fake classifier: known match wins; no known match + review signal returns review_required/policy_model_signal; below threshold returns allowed/model_below_threshold.
6. Implement scan orchestration using `DecisionEngine` and optional model factory/config.
7. Write failing docs assertions for PDQ truthfulness and operator production requirements.
8. Update README/API/operator/release docs.
9. Run focused tests first, then broader verification after behavior stabilizes.

## Manual QA sequence
1. Create synthetic operator hashbank outside tests under `data/hashbanks/operator-known-match.jsonl`.
2. Configure `.env`: `BIG_BROTHER_DEV_MODE=false`, strong `BIG_BROTHER_ADMIN_TOKEN`, `BIG_BROTHER_HASHBANK_PATH=/data/hashbanks/operator-known-match.jsonl`, model triage disabled for baseline.
3. `docker compose up -d --build`.
4. Run `./scripts/health-check.sh`.
5. `curl /v1/hashbank/import-status` shows active entries and `/data/hashbanks/...`.
6. Upload synthetic known fixture to `/v1/scan`; expect `blocked` and `known_illegal_match`.
7. Upload synthetic unknown image; expect allowed/no known match when model disabled.
8. Verify review override and audit export require admin token in production mode.
9. If model triage enabled with local config/model, repeat unknown upload and verify review/no_action threshold behavior without illegal decision.
10. Verify audit JSONL exists and image bytes are not stored.
11. Negative QA: missing production hashbank path fails clearly and does not run fixture/empty hashbank.

## Commit/push approach
Protect user work by inspecting final diff before commit. Commit after green focused verification in small logical commits: (1) production hashbank/container config, (2) optional scan triage or truthful scope correction, (3) docs hardening. Run full verification before final commit/push. Push to `main` only after acceptance and manual QA evidence are recorded in ultragoal. No force-push.

## Acceptance criteria
- Production API defaults no longer load `tests/fixtures/hashbanks/known-match.jsonl` or silently fall back to it.
- Production Docker image no longer copies fixture hashbanks.
- Compose provides operator-controlled read-only hashbank mount and env path.
- Missing/invalid production hashbank fails explicitly or reports unmistakable non-ready state; never scans fixture/empty silently.
- `/v1/hashbank/import-status` reports configured path and active entries.
- `/v1/scan` SHA known match remains blocked with `known_illegal_match`.
- Optional model triage, if implemented, is disabled by default, local-only, operator-configured, and cannot produce illegal/model-only legal finding.
- PDQ upload scanning is either genuinely implemented with tested image-to-PDQ computation or docs state PDQ is matcher/hashbank support only, not upload scan behavior.
- README/API/operator/release docs truthfully describe behavior, limitations, operator duties, and production safety.
- Tests cover hashbank loading/failure, Compose/Dockerfile config, scan precedence, optional model triage, and docs truthfulness.
- Manual QA covers Compose start, health, import status, known/unknown uploads, admin-token endpoints, audit export, and missing-hashbank failure.
- Final work is committed and pushed to `main` only after verification; planning stage changes no product source.

## Production safety notes
Use authorized hash sources only; do not store real illegal media in repo; keep hashbank mount read-only; set `BIG_BROTHER_DEV_MODE=false` and rotate admin token before production; keep model weights/operator configs local and license-reviewed; no external endpoints or telemetry by default; document audit retention/export/deletion; run false-positive override drill; treat empty hashbank as unsafe for production.

## Verification commands for ultragoal execution
Focused: `uv run pytest tests/api/test_scan_endpoint.py`; `uv run pytest tests/install/test_compose.py`; `uv run pytest tests/docs tests/security`; `uv run pytest tests/models tests/decision`.
Final: `uv run pytest`; `uv run ruff check .`; `uv run basedpyright`; `docker compose config`; `docker compose up -d --build` plus manual QA and `docker compose down`.

## Risks and mitigations
- Empty/invalid hashbank: production failure and import-status verification.
- Overclaimed docs: docs tests and exact scope language.
- Missing model deps: disabled default, explicit enablement, clear config errors, no fake fallback.
- Model-only overblocking: route through existing policy/decision types and test known-match precedence plus illegal rejection.
- Unauthorized mutable hashbanks: read-only mount and operator authorization checklist.
- Sensitive logs: no image bytes, documented retention/export controls.

## Handoff
Hand off to ultragoal for durable execution ledger. Use executor slices for API/container config, scan/model orchestration, and docs/tests. Run architect if API/runtime config changes materially; run critic before commit/push for docs truthfulness and deployment risk closure. Use team only if parallel implementation lanes become necessary.
