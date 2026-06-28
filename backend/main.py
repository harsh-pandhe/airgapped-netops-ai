from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
import psutil
import ml_model
import rag_system
from graph_manager import manager
from metrics_utils import metrics, get_avg_inference_ms, get_avg_retrieval_ms, get_total_tokens
from hardware_monitor import get_system_metrics
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        print("Starting up NetOps AI backend...")
        # Warm up psutil so first cpu_percent() call returns real value, not 0%
        psutil.cpu_percent(interval=None)

        ml_model.train_model()
        rag_system.init_rag()
        manager.seed_data()

        # Phase 3: Schedule daily retraining
        scheduler.add_job(
            ml_model.run_daily_retraining_pipeline,
            trigger="interval",
            hours=24,
            id="daily_retrain",
            replace_existing=True,
        )
        scheduler.start()
        print("Daily retraining scheduler started (every 24h).")

    except Exception as e:
        print(f"Startup initialization error: {e}")

    yield

    scheduler.shutdown(wait=False)
    print("Shutting down...")


app = FastAPI(title="Air-Gapped NetOps AI", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PredictRequest(BaseModel):
    cpu_usage: float
    memory_usage: float
    temperature: float
    latency: float
    packet_loss: float

class ChatRequest(BaseModel):
    message: str

class FeedbackRequest(BaseModel):
    timestamp: str
    nodeId: str
    isCorrect: bool


@app.get("/")
def read_root():
    return {"message": "NetOps AI Backend Online"}

@app.post("/api/predict")
def predict(data: PredictRequest):
    result = ml_model.predict_node(
        data.cpu_usage, data.memory_usage, data.temperature, data.latency, data.packet_loss
    )
    status = 'critical' if result.get('anomaly') else 'healthy'
    return {"prediction": status}

@app.post("/api/chat")
def chat(data: ChatRequest):
    return {"reply": rag_system.query_chat(data.message)}

@app.get("/api/topology")
async def get_network_topology():
    return manager.get_graph_data()

@app.get("/api/live-state")
async def get_live_state():
    """Returns raw telemetry inputs (cpu, memory, temp, latency, packet_loss) per node."""
    return {
        "RTR-001": {"cpu": 45.0, "memory": 60.0, "temperature": 55.0, "latency": 20.0, "packet_loss": 0.1},
        "RTR-002": {"cpu": 95.0, "memory": 95.0, "temperature": 88.0, "latency": 150.0, "packet_loss": 25.0},
        "SW-001":  {"cpu": 20.0, "memory": 30.0, "temperature": 40.0, "latency": 5.0,   "packet_loss": 0.0},
        "FW-001":  {"cpu": 85.0, "memory": 70.0, "temperature": 60.0, "latency": 50.0,  "packet_loss": 2.0},
    }

@app.get("/api/predict-all")
async def get_all_predictions():
    return {
        "RTR-001": ml_model.predict_node(45.0, 60.0, 55.0, 20.0, 0.1),
        "RTR-002": ml_model.predict_node(95.0, 95.0, 88.0, 150.0, 25.0),
        "SW-001": ml_model.predict_node(20.0, 30.0, 40.0, 5.0, 0.0),
        "FW-001": ml_model.predict_node(85.0, 70.0, 60.0, 50.0, 2.0),
    }

@app.post("/api/feedback")
async def handle_feedback(data: FeedbackRequest):
    if not data.isCorrect:
        ml_model.flag_false_positive(data.timestamp)
        return {"status": "Model adjusted - False positive logged"}
    return {"status": "Feedback noted - True positive confirmed"}

@app.get("/api/metrics")
async def get_metrics():
    hardware = get_system_metrics()
    return {
        "avg_inference_ms": round(get_avg_inference_ms(), 2),
        "avg_retrieval_ms": round(get_avg_retrieval_ms(), 2),
        "total_tokens": get_total_tokens(),
        "hardware": hardware,
    }

class DeviceRequest(BaseModel):
    node_id: str
    label: str
    ip: str

class ConnectionRequest(BaseModel):
    source: str
    target: str

class DeviceUpdateRequest(BaseModel):
    node_id: str
    data: dict


@app.post("/api/topology/device")
async def add_device(req: DeviceRequest):
    manager.add_device(req.node_id, {"label": req.label, "ip": req.ip})
    return {"status": "added", "node_id": req.node_id}

@app.delete("/api/topology/device/{node_id}")
async def remove_device(node_id: str):
    success = manager.remove_device(node_id)
    if not success:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"{node_id} not found in graph.")
    return {"status": "removed", "node_id": node_id}

@app.patch("/api/topology/device")
async def update_device(req: DeviceUpdateRequest):
    success = manager.update_device(req.node_id, req.data)
    if not success:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"{req.node_id} not found in graph.")
    return {"status": "updated", "node_id": req.node_id}

@app.post("/api/topology/connection")
async def add_connection(req: ConnectionRequest):
    success = manager.add_connection(req.source, req.target)
    if not success:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="One or both nodes not found.")
    return {"status": "connected", "source": req.source, "target": req.target}

@app.delete("/api/topology/connection")
async def remove_connection(req: ConnectionRequest):
    success = manager.remove_connection(req.source, req.target)
    if not success:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Connection not found.")
    return {"status": "removed", "source": req.source, "target": req.target}


@app.post("/api/retrain")
async def trigger_retrain():
    """Manual retrain trigger (useful for testing without waiting 24h)."""
    success = ml_model.run_daily_retraining_pipeline()
    return {"status": "retrained" if success else "insufficient_data"}