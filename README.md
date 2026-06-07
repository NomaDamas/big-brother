# big-brother

`big-brother` is MIT-licensed compliance-support tooling for operators that
need to analyze user-posted photos on their own Linux server with an NVIDIA
GPU.

This project is not legal advice and does not guarantee compliance with Korean
law or any other law. It is designed to provide auditable software building
blocks for known-content hash matching, optional model-based review triage, and
operator-controlled moderation workflows.

The initial implementation target is a one-server Docker Compose deployment
with a FastAPI control plane and NVIDIA Triton for model serving. Real illegal
media, restricted hash lists, and non-redistributable model weights are not
bundled.
