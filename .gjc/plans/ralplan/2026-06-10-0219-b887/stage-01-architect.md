# Architect review: readiness gap ralplan

## Summary
The stage-01 planner artifact is architecturally sound for the four readiness gaps and should proceed to ultragoal execution with `WATCH` status rather than `CLEAR`. The plan correctly prioritizes removing production fixture hashbanks, making PDQ upload scope truthful, and keeping model triage opt-in, but execution must treat the model path as a real backend contract, not a nominal wiring exercise.

## Analysis
- **Production hashbank loading:** Current runtime violates the production boundary. `src/big_brother/api/app.py` creates the default app with `_load_default_entries()` and `hashbank_path=Path("tests/fixtures/hashbanks/known-match.jsonl")`; `_load_default_entries()` silently returns an empty tuple when the fixture is missing or invalid. `Dockerfile` copies `tests/fixtures/hashbanks` into the production image, and `docker-compose.yml` has no operator hashbank mount or `BIG_BROTHER_HASHBANK_PATH`. The plan directly fixes the architecture by moving to operator-owned env/config, removing fixture packaging, using a read-only Compose mount, exposing import status, and requiring explicit failure or unmistakable non-ready state in production.
- **PDQ upload scan path or truthful docs:** `KnownContentMatcher.scan()` computes SHA-256 only. PDQ exists as `scan_pdq(hash_value)` for a precomputed PDQ value, not as image upload hashing. README currently advertises SHA-256 and PDQ known-content matching broadly enough to be read as upload behavior. The plan is sound because it refuses fake PDQ upload support and requires either genuine image-to-PDQ computation with tests and dependency review, or documentation that PDQ is matcher/hashbank support only.
- **Optional model triage or truthful README scope:** The domain pieces are real: `DecisionEngine` gives known-match precedence and `ModerationDecision.from_model_signal()` prevents model-only illegal outcomes; `TransformersImageModerationClient` and `TritonModelAdapter` can produce `ModelSignal`s. `/v1/scan` does not invoke them today. Option B is feasible only if execution defines a classifier protocol/factory, constructs clients at app creation or startup, keeps triage disabled by default, validates enabled config explicitly, and avoids blocking the FastAPI event loop with synchronous PIL/GPU inference. The current Dockerfile installs base dependencies only, while Hugging Face triage needs the optional `gpu` dependency group; the Triton adapter is only a protocol wrapper, not a complete remote client.
- **Production deploy and operator hardening:** The plan covers the missing deployment controls: Compose env and volumes, `.env.example`, operator guide, release checklist, admin-token QA, audit image-free behavior, and missing-hashbank failure. One extra readiness detail should be included: production mode with an empty `BIG_BROTHER_ADMIN_TOKEN` currently starts but protected review and audit endpoints cannot be used, so production config validation or readiness output should surface this as non-ready.

## Strongest steelman antithesis
The strongest argument against the chosen Option B is that readiness is first a safety and truthfulness problem, not a feature parity problem. Adding model triage in the same pass can introduce GPU dependency drift, cold-start failures, latency spikes, event-loop blocking, backend-selection ambiguity, and false-positive operational semantics before the fixture hashbank defect is fixed. A stricter Option A would harden hashbank loading, containers, and documentation faster, then narrow README claims until model serving has a separately proven deployment backend and timeout policy.

## Synthesis
Proceed with Option B only under a staged guardrail: land production hashbank, container, and documentation hardening first; then add model triage only if there is a concrete tested backend seam with disabled-by-default config, startup validation, known-match precedence, off-event-loop or batched inference, and no model-only illegal result. If those conditions cannot be met during execution, fall back to truthful README/API/operator wording instead of weakening the core production-safety work. Do not implement PDQ upload scan unless a real image-to-PDQ path is added with tests, license review, and normalization decisions.

## Findings
- **MEDIUM - Model triage backend boundary is underspecified.** References: `src/big_brother/api/app.py`, `src/big_brother/models/hf_moderation.py`, `src/big_brother/models/triton.py`, `pyproject.toml`, `Dockerfile`. Impact: a nominal scan integration could block the event loop, fail in the production image because optional GPU dependencies are absent, or imply Triton support without a concrete client. Fix: add an injected classifier protocol/factory, instantiate once, validate enabled config, and run synchronous classification through an offload or batcher path.
- **LOW - Production admin-token absence should be visible as non-ready config.** References: `src/big_brother/api/app.py`, `docker-compose.yml`, `.env.example`, `docs/operator-guide.md`. Impact: `BIG_BROTHER_DEV_MODE=false` with no token starts but makes review override and audit export unusable. Fix: fail startup or expose an unmistakable readiness/config error for missing or placeholder admin tokens in production mode.
- **LOW - Docs truthfulness tests need broader public-surface coverage.** References: `tests/docs/test_compliance_docs.py`, `README.md`, `docs/api.md`, `docs/operator-guide.md`. Impact: overclaimed PDQ upload or model-triage behavior can reappear outside the current compliance/model-policy assertions. Fix: assert the public docs describe `/v1/scan` behavior exactly and distinguish SHA upload matching, precomputed PDQ matcher support, and optional enabled model triage.

## Principle violations
- Current code violates Principle 1 by loading and packaging test fixture hashbanks in production defaults.
- Current public README/API language risks violating Principle 2 because PDQ and model triage are broader than observable `/v1/scan` behavior.
- The plan itself does not violate the listed principles if execution keeps fail-fast production validation, local-only operator-owned configuration, docs honesty, and no model-only illegality.

## Recommendations
1. Keep the planner priority order: production hashbank fail-fast and container config first, public documentation truthfulness second, optional model triage only after backend seams are explicit.
2. Treat empty active hashbanks and missing production admin tokens as non-ready production states.
3. Use dependency injection for model classification and never construct model clients per request.
4. Leave PDQ upload scan out of scope unless real image-to-PDQ computation is introduced with tests and dependency/license review.

## Architectural Status
`WATCH`

## Code Review Recommendation
`COMMENT`

## Trade-offs
| Tension | Safer option | Feature-complete option | Architectural call |
| --- | --- | --- | --- |
| Truthful docs vs feature completion | Narrow README/API to observed behavior | Implement model and PDQ paths to match current promises | Narrow PDQ now; implement model only with a tested opt-in backend seam. |
| Fail-fast production config vs dev ergonomics | Reject missing or empty production hashbank and missing token | Allow startup and rely on import-status checks | Production should fail or report non-ready unmistakably; dev/test injection can stay ergonomic. |
| Simple sync model call vs robust serving | Direct classifier call inside `/v1/scan` | Startup-created injected client with offload or batching | Use injection plus offload/batcher to avoid event-loop and cold-start hazards. |
