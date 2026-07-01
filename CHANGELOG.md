# Changelog

All notable changes to this project are documented here. Format based on
[Keep a Changelog](https://keepachangelog.com/); versioning aims for
[SemVer](https://semver.org/).

## [Unreleased]

### Added
- Product roadmap ([docs/ROADMAP.md](docs/ROADMAP.md)) with PS-13 gap analysis and epics.
- Repository governance: `CONTRIBUTING.md`, `SECURITY.md`, issue/PR templates, `.env.example`.

### Security
- Password hashing migrated from unsalted SHA-256 to **bcrypt**.
- Default demo accounts no longer seeded in non-demo deployments (gated by `DEMO_MODE` or
  explicit password env vars).
- `/api/demo/inject` and `/api/demo/reset` now require `can_crud_topology` and are
  audit-logged.

### Fixed
- Retraining pipeline no longer crashes when the model directory does not exist
  (`os.makedirs(..., exist_ok=True)` before `joblib.dump`).

## [0.1.0] — MVP

- Local Isolation Forest anomaly detection with SHAP explanations and feedback loop.
- Offline RAG copilot (Chroma + bge-reranker + local Ollama).
- Topology knowledge graph, JWT auth + RBAC, hash-chained audit log, local observability,
  WebSocket telemetry, demo fault-injection scenarios, Docker packaging.
