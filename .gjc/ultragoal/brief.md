Execute approved ralplan `/data/home/jeffrey/Projects-dev/big-brother/.gjc/plans/ralplan/2026-06-10-0219-b887/pending-approval.md`. User explicitly approved TDD, manual QA, commit well, and push to main.

Constraints: preserve local-first/no-telemetry, no real illegal media, no external reporting, no fake PDQ/model integrations, fail explicitly for unsafe production config, verify with focused and full gates, inspect diff before commit, push to main without force-push.

@goal: Harden production hashbank and deployment config
Implement env-backed production hashbank loading for API/default app, remove test fixture hashbank defaults from production Docker image, add Compose read-only operator hashbank mount/env and production-safe `.env.example`, fail explicitly or report unmistakably non-ready when production hashbank/admin token config is missing, invalid, empty, or placeholder.

@goal: Align scan behavior for PDQ and optional model triage
Keep SHA known-match precedence, do not claim PDQ upload scanning without real image-to-PDQ computation, add optional local model triage through a safe disabled-by-default injected backend seam if feasible using existing code, otherwise narrow docs truthfully. Model signal must never create a model-only illegal decision.

@goal: Harden public docs and operator runbook
Update README, API docs, operator guide, release checklist, and docs tests so operators can run production-like local deployment with explicit hashbank/model config, admin token enforcement, audit export, manual QA, and truthful PDQ/model scope.

@goal: Verify, manual QA, commit, and push
Run focused tests during TDD, full pytest/ruff/basedpyright/docker compose config, manual API/CLI QA. Attempt Docker build/Compose runtime QA and record if daemon permission blocks. Inspect final diff, commit logically, and push to main.
