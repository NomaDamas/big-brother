# Model Policy

Unknown-content classifiers are optional triage inputs. A model signal must not determine illegality. The default domain rule is that a model-only signal can
produce `no_action`, `review_required`, or `policy_blocked`, but not `illegal`.

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
| PDQ known match within distance threshold | `blocked` | Threshold evidence and audit |
| Unknown-content classifier below threshold | `no_action` | Continue normal non-model decision flow |
| Unknown-content classifier above threshold | `review_required` or `policy_blocked` | Human review or operator policy |
| Model unavailable | `review_required` | Retry, fallback, or manual queue |

## Default classifier threshold

The Slurm GPU verification config uses `Falconsai/nsfw_image_detection`, whose
current Hugging Face model card lists Apache-2.0 licensing. The default
threshold is `0.7` for labels `nsfw`, `explicit`, `porn`, and `sexy`.

- Owner: security
- Review date: 2026-06-07
- Rationale: route high-confidence explicit classifier output to human review;
  below-threshold output records `no_action` and must not become an illegality
  finding.

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
optional FAISS indexing, the synthetic `fixture_classifier`, and the optional
`Falconsai/nsfw_image_detection` classifier. No default entry may have an empty
license, unknown license, or noncommercial-only license.

## Secrets and telemetry

Run:

```bash
uv run big-brother config dump
```

Default runtime telemetry is disabled and no external endpoint is configured.
Operators should set `BIG_BROTHER_ADMIN_TOKEN` in `.env`, keep `.env` out of
version control, and rotate that token after a staff change or suspected leak.
