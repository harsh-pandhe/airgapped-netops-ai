# Security Policy

## Reporting a vulnerability

Do **not** open a public GitHub issue for security vulnerabilities. Report privately via
GitHub Security Advisories (Security tab → *Report a vulnerability*), or contact the
maintainer directly. We aim to acknowledge within 72 hours.

## Air-gap / offline compliance

This platform is designed for regulated, air-gapped deployments. Runtime compliance
requirements:

- **Zero outbound dependency at runtime.** The only permitted network call is to a local
  Ollama instance (`http://localhost:11434`). No telemetry, config, or query data leaves the
  host.
- **Local-only models.** Embeddings (`all-MiniLM-L6-v2`) and reranker
  (`bge-reranker-large`) execute locally.
- **Known caveat:** on first run, model weights may be fetched from the Hugging Face Hub if
  not already cached. For a true air-gap, **pre-bundle all model artifacts** and set
  `HF_HUB_OFFLINE=1` / `TRANSFORMERS_OFFLINE=1`. Tracked in the [ROADMAP](docs/ROADMAP.md)
  (E6). Verify egress is denied before deployment.

## Authentication & secrets

- Passwords are hashed with **bcrypt**. No plaintext or unsalted hashes.
- Auth seeds **no default accounts** unless `DEMO_MODE=true` or explicit
  `DEFAULT_OPERATOR_PASSWORD` / `DEFAULT_ARCHITECT_PASSWORD` env vars are set.
- Set a strong `JWT_SECRET` via environment. Do not use the default in production.
- Privileged actions (topology CRUD, scenario injection, retrain) are gated by RBAC and
  recorded in a hash-chained audit log.

## Supported versions

The `master` branch receives security fixes. Pin dependencies for reproducible offline
builds.
