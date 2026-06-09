# big-brother

**Auditable, local-first image-moderation building blocks for operators who are
*required* to scan user uploads — without handing their users' photos to anyone.**

## Why this exists

From **July 1, 2026**, an amendment to South Korea's Telecommunications Business
Act (전기통신사업법) — in the lineage of the 2021 "Nth Room Prevention Act" — is
being read to require operators of Korean online communities and forums to run
**AI pre-screening on every user-uploaded image and video**.

The mandate lands with hard edges:

- **Operators pay for the compute.** The government does not provide it. Site
  owners are expected to buy and run **datacenter-class NVIDIA GPUs** themselves.
- **The timeline is brutal.** Sites are expected to have the hardware and
  software in place almost overnight, with little lead time and uncertain
  equipment supply.
- **It is contested.** The policy sits on the fault line between online-safety
  arguments and serious concerns about **free expression, cost, and fairness** —
  domestic services carry the burden while many foreign platforms do not.

Background: [GeekNews](https://news.hada.io/topic?id=30222) ·
[PrivacyGuides discussion](https://discuss.privacyguides.net/t/south-korean-online-communities-will-need-to-scan-every-images-with-ai-censorship-tools/38341) ·
[Korean press](https://www.gameple.co.kr/news/articleView.html?idxno=215562)

Reasonable people disagree about the policy. But an operator who has no choice
but to comply should not *also* be forced to ship their users' images to an
opaque third party or a black-box cloud service. The principle behind this
project is simple: **if you must scan, scan on infrastructure you control, in a
way you can audit, that phones home to no one.**

The name is deliberately on the nose. `big-brother` is the surveillance you are
being compelled to run — so it is built to keep the control, the logs, and the
accountability in *your* hands, not someone else's.

## What it is

MIT-licensed compliance-support tooling you run on your **own** Linux + NVIDIA GPU
server, with
**no telemetry and no external endpoints by default**. It provides auditable
building blocks for:

- **Known-content matching** — exact SHA-256 and PDQ perceptual-hash matching
  against authorized hash banks.
- **Optional model triage** — local Hugging Face / Triton classifiers that route
  *uncertain* content to human review. A model signal never decides legality on
  its own; below-threshold output records `no_action`.
- **Operator-controlled workflows** — human review, overrides with required
  reasons, and decision states you can defend.
- **Audit trail** — every model signal, override, and policy change is logged for
  later review.

## What it is NOT

- **Not legal advice.** This software is *not legal advice* and does not guarantee
  compliance with Korean law or any other law. Confirm your obligations with
  counsel.
- **Not a content database.** No real illegal media, no restricted/registered
  hash lists, and no non-redistributable model weights are bundled. You supply
  authorized hash sources and operator-enabled models yourself.
- **Not a cloud service.** There is no SaaS, no phone-home, no external
  reporting. It is yours to run and yours to audit.

## Deployment

The initial target is a single Linux server with an NVIDIA GPU, deployed via
**Docker Compose**: a FastAPI control plane plus **NVIDIA Triton** for model
serving. See [`docs/operator-guide.md`](docs/operator-guide.md) for prerequisites
and [`docs/release-checklist.md`](docs/release-checklist.md) before going live.

```bash
cp .env.example .env   # set BIG_BROTHER_ADMIN_TOKEN before production use
docker compose up -d --build
./scripts/health-check.sh
```

## License

MIT. See [`LICENSE`](LICENSE). Model weights and hash sources are separate
artifacts with their own licenses and authorization requirements; see
[`docs/model-policy.md`](docs/model-policy.md) and
[`docs/compliance.md`](docs/compliance.md).
