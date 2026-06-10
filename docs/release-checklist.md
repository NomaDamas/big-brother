# Release Checklist

- legal-review: confirm current Korean legal obligations with counsel before deployment.
- model-license: verify every enabled model has an approved license and model card.
- hash-source authorization: confirm every imported hash bank source is authorized and documented.
- GPU prerequisite: verify NVIDIA driver, Docker, Compose, and NVIDIA Container Toolkit.
- false-positive drill: run override and appeal workflow with a synthetic fixture.
- incident response: confirm operator contacts, log export, revocation, and deletion workflow.
- privacy review: confirm telemetry remains disabled and no external endpoint is configured.
- security review: rotate `BIG_BROTHER_ADMIN_TOKEN` and audit `.env` handling.
- production-config: set `BIG_BROTHER_DEV_MODE=false`, configure a non-placeholder `BIG_BROTHER_ADMIN_TOKEN`, and verify startup fails for a missing or empty production hash bank.
- hashbank-mount: confirm `./data/hashbanks` is mounted read-only and `BIG_BROTHER_HASHBANK_PATH` points to an authorized JSONL file.
- scan-scope: confirm operators understand upload scans are SHA-256 exact-match by default; PDQ is precomputed matcher/hashbank support until image-to-PDQ upload hashing is implemented.
- model-triage: keep `BIG_BROTHER_MODEL_TRIAGE_ENABLED=false` unless local model dependencies, config, license, and threshold review are complete.
