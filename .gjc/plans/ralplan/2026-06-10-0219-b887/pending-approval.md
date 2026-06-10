# Final RALPLAN: big-brother readiness gaps 1-4

Status: execution approved in current user instruction for ultragoal execution.
Run: 2026-06-10-0219-b887

## Decision
Proceed with Option B from the approved planner artifact: harden production hashbank loading and deployment configuration, keep PDQ upload behavior truthful unless real image-to-PDQ computation exists, add optional local model triage only through a safe disabled-by-default injected backend seam, and harden README/API/operator/release docs. Execute via ultragoal with TDD, manual QA, commit, and push to `main`.

## Drivers
1. Remove production reliance on test fixture hashbanks and silent empty fallback.
2. Make Docker Compose/operator configuration usable and safe for production-like local deployments.
3. Ensure public docs match observable `/v1/scan` behavior for SHA, PDQ, and optional model triage.
4. Preserve local-first/no-telemetry and no model-only illegality invariants.

## Alternatives considered

### Option A: hashbank hardening plus truthful docs only
Lower implementation risk and quickest safety fix, but leaves model triage claim weakened despite existing model/policy components.

### Option B: hashbank hardening plus optional model triage, truthful PDQ upload correction
Chosen. Balances implementation with safety: uses existing decision/model primitives where feasible, removes fixture defaults, and avoids fake PDQ upload support.

### Option C: hashbank hardening plus PDQ upload plus model triage
Rejected for this pass. No inspected real image-to-PDQ computation path exists; adding it safely requires dependency, license, and normalization review.

## Architectural guardrails
- No test fixture defaults in production runtime paths.
- Production missing, invalid, or empty hashbank must fail explicitly or be unmistakably non-ready; never silently scan fixture or empty data.
- Missing or placeholder admin token in production must be visible as non-ready/fail-fast.
- PDQ upload scan must not be claimed unless actual tested image-to-PDQ computation exists.
- Model triage must be disabled by default, local/operator-configured, startup-validated, and incapable of model-only illegal decisions.
- Model clients must not be constructed per request; synchronous GPU/PIL work must be offloaded or batched.

## Execution plan
1. Add failing API tests for env hashbank loading, production missing/invalid hashbank failure, production token readiness, import status, known-match precedence, optional model triage review/no_action, and max upload/non-image preservation.
2. Implement `ApiSettings`/default-app env loading for `BIG_BROTHER_HASHBANK_PATH`, audit path, max upload bytes, dev mode, admin token, and optional model triage configuration. Preserve direct test injection.
3. Remove production fixture hashbank copy from Dockerfile. Add Compose read-only operator hashbank mount/env and update `.env.example`.
4. Add/adjust install tests for Compose/Dockerfile production config.
5. Wire optional triage after known-match scan through `DecisionEngine` using an injected classifier protocol or narrow docs if a safe backend cannot be completed. Do not fake Triton or PDQ upload support.
6. Update README, API docs, operator guide, release checklist, and docs tests for truthful behavior and production runbook.
7. Run focused tests, then full verification: `uv run pytest`, `uv run ruff check .`, `uv run basedpyright`, `docker compose config`, manual QA. Attempt Docker build/Compose QA; record if host Docker permission blocks execution.
8. Inspect diff, commit logical changes, push to `main` without force-push.

## TDD sequence
- Focused API tests before API changes.
- Install/Compose/Dockerfile tests before deployment config changes.
- Docs truthfulness tests before docs edits.
- Focused test runs after each lane, full suite at the end.

## Manual QA
- Generate or reuse synthetic operator hashbank outside `tests/`.
- Configure production-like `.env` with `BIG_BROTHER_DEV_MODE=false`, real admin token, configured hashbank path, model disabled baseline.
- Run Compose config/build/up where permitted, health check, import status, known upload blocked, unknown upload allowed/model-disabled, admin-token negative/positive checks, audit export, and missing-hashbank negative start/readiness check.

## Acceptance criteria
- Production API no longer loads `tests/fixtures/hashbanks/known-match.jsonl` by default.
- Docker image no longer copies fixture hashbanks.
- Compose exposes operator-controlled read-only hashbank mount and env path.
- Missing/invalid production hashbank and missing production admin token are explicit failures/non-ready states.
- `/v1/hashbank/import-status` reports configured path and active entries.
- `/v1/scan` known SHA match remains blocked with `known_illegal_match`.
- Optional model triage is disabled by default, local-only, operator-configured, and cannot produce illegal/model-only decisions.
- PDQ upload behavior is either actually implemented and tested or public docs clearly state PDQ support is precomputed matcher/hashbank support, not upload scanning.
- Tests and manual QA evidence support final commit.

## ADR

### Why chosen
This prioritizes production safety and truthful operator expectations over pretending feature completeness. It may leave full PDQ image upload matching for a later dedicated implementation, but removes the most dangerous readiness gap: fixture/empty production scanning.

### Consequences
Operators must configure an explicit hashbank for production. Docs become more precise about PDQ and model triage. Optional model triage remains controlled and disabled by default.

### Follow-ups
- Dedicated PDQ image hashing implementation with dependency/license/normalization review.
- Concrete Triton remote client/backpressure/timeout implementation if operator deployments require Triton-backed `/v1/scan` model triage.
- Expanded operations docs for retention, backup, upgrade/rollback, and incident drills after MVP hardening lands.
