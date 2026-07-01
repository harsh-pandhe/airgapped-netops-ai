# Air-Gapped NetOps AI — Predictive Copilot for Secure MPLS Operations

An autonomous, **fully air-gapped** NOC copilot that predicts network degradation before
service impact, explains its reasoning in natural language, and runs entirely offline — no
cloud APIs, no outbound inference. Built for regulated and government SD-WAN / MPLS
environments where cloud-connected AI is prohibited.

> **Problem framing (SIH PS-13):** conventional NOC tooling is *reactive* — alerts fire
> only after thresholds are breached. This platform aims to be *predictive*: forecast
> degradation with enough lead time for operators to intervene, and communicate that
> forecast in operator-ready language without leaving the air-gapped boundary.

---

## What it does today

| Capability | Status | Module |
|---|---|---|
| Local telemetry ingestion (mock + SNMP stub) | ✅ Working | [`telemetry_poller.py`](backend/telemetry_poller.py) |
| WebSocket live telemetry stream | ✅ Working | [`telemetry_ws.py`](backend/telemetry_ws.py) |
| Unsupervised anomaly **detection** (Isolation Forest + SHAP) | ✅ Working | [`ml_model.py`](backend/ml_model.py) |
| Offline RAG copilot (Chroma + bge-reranker + local Ollama) | ✅ Working | [`rag_system.py`](backend/rag_system.py) |
| Topology knowledge graph (NetworkX) | ✅ Working | [`graph_manager.py`](backend/graph_manager.py) |
| JWT auth + RBAC + hash-chained audit log | ✅ Working | [`auth.py`](backend/auth.py), [`audit_log.py`](backend/audit_log.py) |
| Local observability (tokens, latency, retrieval metrics) | ✅ Working | [`metrics_utils.py`](backend/metrics_utils.py) |
| Demo fault injection (ddos / link flap / thermal / cascade) | ✅ Working | [`scenarios.py`](backend/scenarios.py) |
| Time-series **forecasting** + time-to-impact | 🚧 Planned | see [ROADMAP](docs/ROADMAP.md) |
| Real MPLS / BGP / OSPF / tunnel simulation | 🚧 Planned | see [ROADMAP](docs/ROADMAP.md) |
| Pre-bundled offline model artifacts | 🚧 Planned | see [ROADMAP](docs/ROADMAP.md) |
| Automated playbook / remediation suggestion | 🚧 Planned | see [ROADMAP](docs/ROADMAP.md) |

The current build **detects** anomalies well and delivers a genuinely offline copilot. The
[product roadmap](docs/ROADMAP.md) tracks the gap to a full PS-13-grade predictive platform:
forecasting with lead time, realistic MPLS/SD-WAN telemetry, and closed-loop remediation.

---

## Architecture

```
┌──────────────── Frontend (React + TS + Vite, served via nginx) ────────────────┐
│  App.tsx · TopologyView · ObservabilityTab                                      │
│  chat copilot · live charts · anomaly feed · WebSocket stream                   │
└───────────────────────────────────┬─────────────────────────────────────────────┘
                                     │ REST + WebSocket
┌───────────────────────────────────┴─────────────────────────────────────────────┐
│  FastAPI (main.py) — JWT auth · RBAC · hash-chained audit                         │
├───────────────────────────────────────────────────────────────────────────────────┤
│  telemetry_poller  Mock / SNMP source → live node state                           │
│  ml_model          Isolation Forest anomaly detection · SHAP · retrain · feedback │
│  rag_system        Chroma vector store · bge-reranker · intent routing · Ollama   │
│  graph_manager     NetworkX topology graph                                        │
│  scenarios         fault injection for demo / validation                          │
│  metrics_utils     token / latency / retrieval metrics                            │
│  audit_log         tamper-evident hash-chained event log                          │
└───────────────────────────────────────────────────────────────────────────────────┘
     SQLite: auth.db · metrics.db · audit.db        CSV: telemetry logs
     Local Ollama (default qwen2.5:3b) — the ONLY localhost service call
```

**Air-gap posture:** the only outbound call at runtime is to a local Ollama instance
(`http://localhost:11434`). Embeddings (`all-MiniLM-L6-v2`) and the reranker
(`bge-reranker-large`) run locally. See [SECURITY.md](SECURITY.md) for the offline-compliance
checklist — note the first-run model download caveat, tracked as a roadmap item.

---

## Prerequisites

- **Python** 3.10+
- **Node.js** 18+ (with npm)
- **Ollama** running locally with a model pulled:
  ```bash
  ollama pull qwen2.5:3b   # default; override with OLLAMA_MODEL
  ```

---

## Getting Started

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Optional: enable demo accounts (operator / architect). Off by default.
export DEMO_MODE=true

uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

The Isolation Forest model trains and the RAG pipeline initializes from the local dataset on
startup. Copy [`.env.example`](.env.example) to `.env` and adjust as needed.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173/`.

### Docker (full stack)

```bash
docker compose up --build
```

---

## Authentication

Auth is **on by default** and seeds **no accounts** in a non-demo deployment. To create the
demo `operator` / `architect` users, either set `DEMO_MODE=true` or provide
`DEFAULT_OPERATOR_PASSWORD` / `DEFAULT_ARCHITECT_PASSWORD` explicitly. Passwords are stored
with **bcrypt**. See [SECURITY.md](SECURITY.md).

---

## Testing

```bash
cd backend
source venv/bin/activate
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest
```

---

## Documentation

- [ROADMAP.md](docs/ROADMAP.md) — product-level roadmap and PS-13 gap analysis
- [SECURITY.md](SECURITY.md) — air-gap compliance and vulnerability reporting
- [CONTRIBUTING.md](CONTRIBUTING.md) — dev setup, branch, and PR conventions
- [implementation_plan.md](docs/implementation_plan.md) — original MVP transformation plan

---

## License

MIT — see [LICENSE](LICENSE).
