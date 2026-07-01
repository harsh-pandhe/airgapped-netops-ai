# Product Roadmap — Air-Gapped NetOps AI

Roadmap to take the current MVP to a **product-grade, PS-13-compliant** predictive NOC
copilot. Grounded in Problem Statement 13 (Air-Gapped Predictive Copilot for Secure MPLS
Operations) and its four evaluation dimensions.

## Where we are vs PS-13

| PS-13 Objective | Current state | Gap |
|---|---|---|
| **1. Simulated SD-WAN/MPLS** | 4-device NetworkX label graph + mock random-walk telemetry | No MPLS forwarding, VPN segmentation, BGP/OSPF, IPSec overlays, QoS, or real simulator |
| **2. Predictive fault analytics** | Isolation Forest point-anomaly **detection** + SHAP | No **forecasting**, no time-to-impact, no routing/tunnel-specific models |
| **3. Offline LLM copilot** | Ollama + Chroma + reranker + structured prompts | Strong; needs pre-bundled offline artifacts and grounded-citation hardening |
| **4. NOC workflow automation** | Anomaly feed, mitigation prompts, demo scenarios | No graph event correlation, playbook automation, or incident summarization |

## Evaluation alignment

| Dimension | Weight | Roadmap epics |
|---|---:|---|
| Technical Merit (prediction accuracy + lead time) | 35% | E1, E2, E3 |
| Copilot Effectiveness (grounded, no hallucination) | 35% | E4, E5 |
| Security & Offline Compliance | 20% | E6, E7 |
| Documentation Quality | 10% | E8 |

## Epics → Issues

- **E1 — Realistic SD-WAN/MPLS simulation** (Containerlab/GNS3; CE/PE/P; MPLS, VPN, BGP/OSPF, IPSec, QoS)
- **E2 — Time-series forecasting + time-to-impact** (LSTM/Prophet; congestion, utilization, latency drift; lead-time estimation)
- **E3 — Routing & tunnel health analytics** (BGP/OSPF instability, route-flap precursors, tunnel degradation scoring)
- **E4 — Grounded copilot & citation hardening** (structured payload: predicted issue, confidence, root-cause, scope, time-to-impact; anti-hallucination eval)
- **E5 — NOC workflow automation** (graph event correlation, confidence-scored prioritization, playbook suggestion, incident summaries)
- **E6 — Verifiable air-gap & offline model bundling** (pre-bundle HF/Ollama artifacts, egress-deny verification, offline install)
- **E7 — Security hardening** (secrets/JWT config, rate limiting, input validation, dependency pinning)
- **E8 — Packaging, CI/CD, docs & test coverage** (portable bundle, coverage gate, architecture docs, operator runbook)

See GitHub Issues for the full task list, milestones, and acceptance criteria.
