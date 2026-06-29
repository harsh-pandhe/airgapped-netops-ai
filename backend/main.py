"""
main.py — SENTINEL-MPLS FastAPI backend.
Wires: Auth(5), Tests(6), Poller(9), Observability(10), WS(13), XAI(14), Agentic(15), Demo(16)
"""

from fastapi import FastAPI, HTTPException, Depends, Request, WebSocket, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from contextlib import asynccontextmanager
from typing import Optional
import psutil

import ml_model
import rag_system
from graph_manager import manager
from metrics_utils import (
    metrics, get_avg_inference_ms, get_avg_retrieval_ms,
    get_total_tokens, get_metric_history,
    get_mitigation_success_rate, get_avg_reranker_score,
)
from hardware_monitor import get_system_metrics
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telemetry_poller import engine
from telemetry_ws import telemetry_broadcast_loop
from scenarios import inject_scenario, reset_scenarios, get_scenario_list
from auth import (
    authenticate_user, create_access_token, get_current_user,
    require_permission, check_node_access, seed_default_users,
    Token, TokenData,
)
from audit_log import log_event, get_audit_log, verify_integrity

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        print("Starting SENTINEL-MPLS backend...")
        psutil.cpu_percent(interval=None)           # warm up psutil
        ml_model.train_model()
        rag_system.init_rag()
        manager.seed_data()
        engine.start()                              # live telemetry poller
        seed_default_users()                        # RBAC default accounts

        scheduler.add_job(
            ml_model.run_daily_retraining_pipeline,
            trigger="interval", hours=24,
            id="daily_retrain", replace_existing=True,
        )
        scheduler.start()
        print("Startup complete.")
    except Exception as e:
        print(f"Startup error: {e}")
    yield
    scheduler.shutdown(wait=False)
    print("Shutting down.")


app = FastAPI(title="SENTINEL-MPLS NetOps AI", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic models ───────────────────────────────────────────────────────────

class PredictRequest(BaseModel):
    cpu_usage: float; memory_usage: float; temperature: float
    latency: float;   packet_loss: float

class ChatRequest(BaseModel):
    message: str

class FeedbackRequest(BaseModel):
    timestamp: str; nodeId: str; isCorrect: bool

class DeviceRequest(BaseModel):
    node_id: str; label: str; ip: str

class ConnectionRequest(BaseModel):
    source: str; target: str

class DeviceUpdateRequest(BaseModel):
    node_id: str; data: dict


# ── Root ──────────────────────────────────────────────────────────────────────

@app.get("/")
def read_root():
    return {"message": "SENTINEL-MPLS NetOps AI Online"}


# ── Auth (Track 5) ────────────────────────────────────────────────────────────

@app.post("/api/auth/login", response_model=Token)
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    ip   = request.client.host if request.client else "unknown"
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        log_event(form_data.username, "unknown", "LOGIN_FAILURE", ip_address=ip)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    domains = user["domains"].split(",") if user["domains"] != "*" else ["*"]
    token   = create_access_token(user["username"], user["role"], domains)
    log_event(user["username"], user["role"], "LOGIN_SUCCESS", ip_address=ip)
    return Token(access_token=token, token_type="bearer",
                 role=user["role"], domains=domains)

@app.get("/api/auth/me")
async def get_me(user: TokenData = Depends(get_current_user)):
    return {"username": user.username, "role": user.role, "domains": user.domains}


# ── Telemetry (Track 9) ───────────────────────────────────────────────────────

@app.get("/api/live-state")
async def get_live_state(user: TokenData = Depends(require_permission("can_view_telemetry"))):
    live = engine.get_state()
    if "*" not in user.domains:
        from auth import DEVICE_DOMAINS
        live = {k: v for k, v in live.items() if DEVICE_DOMAINS.get(k) in user.domains}
    return live

@app.get("/api/predict-all")
async def get_all_predictions(user: TokenData = Depends(require_permission("can_view_telemetry"))):
    live = engine.get_state()
    if "*" not in user.domains:
        from auth import DEVICE_DOMAINS
        live = {k: v for k, v in live.items() if DEVICE_DOMAINS.get(k) in user.domains}
    return {
        nid: ml_model.predict_node(
            v["cpu"], v["memory"], v["temperature"],
            v["latency"], v["packet_loss"], node_id=nid
        )
        for nid, v in live.items()
    }

@app.post("/api/predict")
def predict(data: PredictRequest,
            user: TokenData = Depends(require_permission("can_view_telemetry"))):
    result = ml_model.predict_node(
        data.cpu_usage, data.memory_usage, data.temperature,
        data.latency, data.packet_loss,
    )
    return {"prediction": "critical" if result["anomaly"] else "healthy", **result}


# ── Node history (Track 8) ────────────────────────────────────────────────────

@app.get("/api/node/{node_id}/history")
async def node_history(
    node_id: str,
    limit: int = 20,
    user: TokenData = Depends(require_permission("can_view_telemetry")),
):
    check_node_access(node_id, user)
    return {"node_id": node_id, "history": ml_model.get_node_history(node_id, limit)}


# ── Chat (Track 5 + 15) ───────────────────────────────────────────────────────

@app.post("/api/chat")
async def chat(request: Request, data: ChatRequest,
               user: TokenData = Depends(require_permission("can_query_rag"))):
    reply = rag_system.query_chat(data.message, user=user)
    log_event(
        user.username, user.role, "RAG_QUERY",
        prompt=data.message, response_summary=reply[:500],
        ip_address=request.client.host if request.client else None,
    )
    return {"reply": reply}


# ── Topology (Track 5 + 11) ───────────────────────────────────────────────────

@app.get("/api/topology")
async def get_topology(user: TokenData = Depends(get_current_user)):
    return manager.get_graph_data()

@app.post("/api/topology/device")
async def add_device(request: Request, req: DeviceRequest,
                     user: TokenData = Depends(require_permission("can_crud_topology"))):
    manager.add_device(req.node_id, {"label": req.label, "ip": req.ip})
    log_event(user.username, user.role, "TOPOLOGY_ADD_NODE", node_id=req.node_id,
              ip_address=request.client.host if request.client else None)
    return {"status": "added", "node_id": req.node_id}

@app.delete("/api/topology/device/{node_id}")
async def remove_device(request: Request, node_id: str,
                        user: TokenData = Depends(require_permission("can_crud_topology"))):
    if not manager.remove_device(node_id):
        raise HTTPException(404, f"{node_id} not found")
    log_event(user.username, user.role, "TOPOLOGY_REMOVE_NODE", node_id=node_id,
              ip_address=request.client.host if request.client else None)
    return {"status": "removed", "node_id": node_id}

@app.patch("/api/topology/device")
async def update_device(req: DeviceUpdateRequest,
                        user: TokenData = Depends(require_permission("can_crud_topology"))):
    if not manager.update_device(req.node_id, req.data):
        raise HTTPException(404, f"{req.node_id} not found")
    return {"status": "updated", "node_id": req.node_id}

@app.post("/api/topology/connection")
async def add_connection(request: Request, req: ConnectionRequest,
                         user: TokenData = Depends(require_permission("can_crud_topology"))):
    if not manager.add_connection(req.source, req.target):
        raise HTTPException(400, "One or both nodes not found")
    log_event(user.username, user.role, "TOPOLOGY_ADD_EDGE",
              metadata={"source": req.source, "target": req.target},
              ip_address=request.client.host if request.client else None)
    return {"status": "connected"}

@app.delete("/api/topology/connection")
async def remove_connection(request: Request, req: ConnectionRequest,
                            user: TokenData = Depends(require_permission("can_crud_topology"))):
    if not manager.remove_connection(req.source, req.target):
        raise HTTPException(404, "Connection not found")
    log_event(user.username, user.role, "TOPOLOGY_REMOVE_EDGE",
              metadata={"source": req.source, "target": req.target},
              ip_address=request.client.host if request.client else None)
    return {"status": "removed"}


# ── Feedback + Retrain ────────────────────────────────────────────────────────

@app.post("/api/feedback")
async def handle_feedback(request: Request, data: FeedbackRequest,
                          user: TokenData = Depends(require_permission("can_view_telemetry"))):
    check_node_access(data.nodeId, user)
    if not data.isCorrect:
        ml_model.flag_false_positive(data.timestamp)
    log_event(user.username, user.role, "FEEDBACK_SUBMITTED", node_id=data.nodeId,
              metadata={"is_correct": data.isCorrect},
              ip_address=request.client.host if request.client else None)
    return {"status": "Model adjusted" if not data.isCorrect else "Feedback noted"}

@app.post("/api/retrain")
async def trigger_retrain(request: Request,
                          user: TokenData = Depends(require_permission("can_trigger_retrain"))):
    success = ml_model.run_daily_retraining_pipeline()
    log_event(user.username, user.role, "RETRAIN_TRIGGERED",
              metadata={"result": "retrained" if success else "insufficient_data"},
              ip_address=request.client.host if request.client else None)
    return {"status": "retrained" if success else "insufficient_data"}


# ── Metrics (Track 10) ────────────────────────────────────────────────────────

@app.get("/api/metrics")
async def get_metrics(user: TokenData = Depends(get_current_user)):
    import os, sqlite3
    from config import DATA_DIR, METRICS_DB_PATH

    hardware = get_system_metrics()

    # Disk usage
    disk = psutil.disk_usage('/')
    hardware["disk_used_gb"]  = round(disk.used / 1e9, 1)
    hardware["disk_total_gb"] = round(disk.total / 1e9, 1)
    hardware["disk_percent"]  = disk.percent

    # Anomaly rate (last 100 predictions)
    anomaly_rate = 0.0
    try:
        import pandas as pd
        acc = os.path.join(DATA_DIR, "accumulated_telemetry.csv")
        if os.path.exists(acc):
            df = pd.read_csv(acc).tail(100)
            preds = [ml_model.predict_node(
                r.cpu_usage, r.memory_usage, r.temperature,
                r.latency, r.packet_loss
            )["anomaly"] for _, r in df.iterrows()]
            anomaly_rate = round(sum(preds) / len(preds) * 100, 1) if preds else 0.0
    except Exception:
        pass

    # FP rate
    fp_rate = 0.0
    try:
        fp_path  = os.path.join(DATA_DIR, "false_positives.csv")
        acc_path = os.path.join(DATA_DIR, "accumulated_telemetry.csv")
        if os.path.exists(fp_path) and os.path.exists(acc_path):
            import pandas as pd
            fp_count  = len(pd.read_csv(fp_path))
            acc_count = len(pd.read_csv(acc_path))
            fp_rate   = round(fp_count / max(acc_count, 1) * 100, 2)
    except Exception:
        pass

    return {
        "avg_inference_ms":        round(get_avg_inference_ms(), 2),
        "avg_retrieval_ms":        round(get_avg_retrieval_ms(), 2),
        "total_tokens":            get_total_tokens(),
        "mitigation_success_rate": get_mitigation_success_rate(),
        "avg_reranker_score":      get_avg_reranker_score(),
        "anomaly_rate_pct":        anomaly_rate,
        "false_positive_rate_pct": fp_rate,
        "shap_fallback_count":     metrics.get("shap_fallback_count", 0),
        "last_retrain":            ml_model.get_last_retrain_timestamp(),
        "hardware":                hardware,
    }

@app.get("/api/metrics/history")
async def metrics_history(
    metric: str = Query(..., pattern="^(inference|retrieval)$"),
    limit:  int = 50,
    user:   TokenData = Depends(get_current_user),
):
    return {"metric": metric, "data": get_metric_history(metric, limit)}

@app.get("/api/snmp/{node_id}")
async def snmp_get(node_id: str,
                   user: TokenData = Depends(require_permission("can_view_telemetry"))):
    check_node_access(node_id, user)
    return engine.snmp_get(node_id)


# ── XAI (Track 14) ───────────────────────────────────────────────────────────

@app.get("/api/xai/history")
async def xai_history(
    node_id: Optional[str] = None,
    limit:   int = 20,
    user:    TokenData = Depends(require_permission("can_view_telemetry")),
):
    if node_id:
        check_node_access(node_id, user)
    return {"data": ml_model.get_shap_history(node_id, limit)}


# ── Audit (Track 5) ──────────────────────────────────────────────────────────

@app.get("/api/audit")
async def get_audit(limit: int = 100, event_type: Optional[str] = None,
                    user: TokenData = Depends(require_permission("can_view_audit_log"))):
    return {"entries": get_audit_log(limit=limit, event_type=event_type)}

@app.get("/api/audit/verify")
async def audit_verify(user: TokenData = Depends(require_permission("can_view_audit_log"))):
    return verify_integrity()


# ── Demo (Track 16) ──────────────────────────────────────────────────────────

@app.get("/api/demo/scenarios")
async def list_scenarios():
    return {"scenarios": get_scenario_list()}

@app.post("/api/demo/inject")
async def inject_demo(scenario: str, user: TokenData = Depends(get_current_user)):
    try:
        result = inject_scenario(scenario, engine)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))

@app.post("/api/demo/reset")
async def reset_demo(user: TokenData = Depends(get_current_user)):
    return reset_scenarios(engine)


# ── WebSocket (Track 13) ─────────────────────────────────────────────────────

@app.websocket("/ws/telemetry")
async def telemetry_ws(websocket: WebSocket):
    await telemetry_broadcast_loop(websocket)