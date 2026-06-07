# Release Checklist

- legal-review: confirm current Korean legal obligations with counsel before deployment.
- model-license: verify every enabled model has an approved license and model card.
- hash-source authorization: confirm every imported hash bank source is authorized and documented.
- GPU prerequisite: verify NVIDIA driver, Docker, Compose, and NVIDIA Container Toolkit.
- false-positive drill: run override and appeal workflow with a synthetic fixture.
- incident response: confirm operator contacts, log export, revocation, and deletion workflow.
- privacy review: confirm telemetry remains disabled and no external endpoint is configured.
- security review: rotate `BIG_BROTHER_ADMIN_TOKEN` and audit `.env` handling.
