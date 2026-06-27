from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
import ml_model
import rag_system
from graph_manager import manager
from metrics_utils import metrics
from hardware_monitor import get_system_metrics

# --- Lifecycle Manager (Modern FastAPI) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Pre-train model and init RAG
    try:
        print("Starting up NetOps AI backend...")
        ml_model.train_model()
        rag_system.init_rag()
        manager.seed_data()
    except Exception as e:
        print(f"Startup initialization error: {e}")
    yield
    # Shutdown logic if needed
    print("Shutting down...")

app = FastAPI(title="Air-Gapped NetOps AI", lifespan=lifespan)

# --- CORS Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins to prevent connection errors
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Data Models ---
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

# --- API Routes ---
@app.get("/")
def read_root():
    return {"message": "NetOps AI Backend Online"}

@app.post("/api/predict")
def predict(data: PredictRequest):
    # Ensure this returns a clean string status like 'healthy' or 'critical'
    result = ml_model.predict_node(
        data.cpu_usage, data.memory_usage, data.temperature, data.latency, data.packet_loss
    )
    # result['anomaly'] is bool, we map it to 'critical' or 'healthy'
    status = 'critical' if result.get('anomaly') else 'healthy'
    return {"prediction": status}

@app.post("/api/chat")
def chat(data: ChatRequest):
    return {"reply": rag_system.query_chat(data.message)}

@app.get("/api/topology")
async def get_network_topology():
    return manager.get_graph_data()

@app.get("/api/predict-all")
async def get_all_predictions():
    """Returns telemetry for all nodes in the sidebar."""
    return {
        "RTR-001": ml_model.predict_node(45.0, 60.0, 55.0, 20.0, 0.1),
        "RTR-002": ml_model.predict_node(95.0, 95.0, 88.0, 150.0, 25.0),
        "SW-001": ml_model.predict_node(20.0, 30.0, 40.0, 5.0, 0.0),
        "FW-001": ml_model.predict_node(85.0, 70.0, 60.0, 50.0, 2.0)
    }

@app.post("/api/feedback")
async def handle_feedback(data: FeedbackRequest):
    if not data.isCorrect:
        ml_model.flag_false_positive(data.timestamp)
        return {"status": "Model adjusted - False positive logged"}
    return {"status": "Feedback noted - True positive confirmed"}

@app.get("/api/metrics")
async def get_metrics():
    # 1. Calculate performance metrics (Inference/Retrieval)
    avg_inf = sum(metrics["inference_times"]) / len(metrics["inference_times"]) if metrics["inference_times"] else 0
    avg_ret = sum(metrics["retrieval_durations"]) / len(metrics["retrieval_durations"]) if metrics["retrieval_durations"] else 0
    
    # 2. Get hardware telemetry
    hardware = get_system_metrics()
    
    # 3. Return everything together
    return {
        "avg_inference_ms": round(avg_inf, 2),
        "avg_retrieval_ms": round(avg_ret, 2),
        "total_tokens": metrics["total_tokens_generated"],
        "hardware": hardware 
    }