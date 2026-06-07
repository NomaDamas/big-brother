# Contributing

Use synthetic fixtures only. Do not submit real illegal media, real restricted
hashes, or unclear-provenance hash lists.

Before opening a change, run:

```bash
uv run ruff check .
uv run basedpyright
uv run pytest
docker compose config
```

Changes that affect moderation behavior need tests, audit evidence, and docs
that preserve the distinction between known-content matches, model triage, and
human decisions.
