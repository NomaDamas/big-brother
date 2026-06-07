# Model Policy

Unknown-content classifiers are optional triage inputs. A model signal must not determine illegality. The default domain rule is that a model-only signal can
produce `review_required` or `policy_blocked`, but not `illegal`.

## Required controls

- Every model has a license entry and model-card review before use.
- Every threshold has an owner, date, and rationale.
- Every `policy_model_signal` is auditable.
- Every human override requires a reason.
- Every false-positive report can be traced to the model version, threshold,
  input metadata, and human decision.

## Default actions

| Signal source | Allowed automatic outcome | Required next step |
| --- | --- | --- |
| Exact SHA-256 known match | `blocked` | Audit and operator workflow |
| PDQ known match above threshold | `blocked` or `review_required` | Threshold evidence and audit |
| Unknown-content classifier | `review_required` or `policy_blocked` | Human review or operator policy |
| Model unavailable | `review_required` | Retry, fallback, or manual queue |

## Model acquisition

The project code is MIT licensed. Model weights are separate artifacts with
their own licenses and dataset limitations. Operators must explicitly opt in to
download or mount model weights, and the service must show the model license
before activation.

## Default license manifest

Run:

```bash
uv run big-brother licenses report
```

The default manifest lists project code, Triton, the PDQ reference ecosystem,
optional FAISS indexing, and the synthetic `fixture_classifier`. No default
entry may have an empty license, unknown license, or noncommercial-only license.

## Secrets and telemetry

Run:

```bash
uv run big-brother config dump
```

Default runtime telemetry is disabled and no external endpoint is configured.
Operators should set `BIG_BROTHER_ADMIN_TOKEN` in `.env`, keep `.env` out of
version control, and rotate that token after a staff change or suspected leak.
