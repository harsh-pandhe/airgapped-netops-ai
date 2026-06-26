from graph_manager import manager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import ml_model
import rag_system
from graph_manager import manager

app = FastAPI(title="Air-Gapped NetOps AI")

from fastapi.middleware.cors import CORSMiddleware

# Add this right after app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # Your frontend URL
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

@app.on_event("startup")
async def startup_event():
    # Pre-train the model and init RAG on startup to save time on first request
    try:
        ml_model.train_model()
        rag_system.init_rag()
        manager.seed_data()
    except Exception as e:
        print(f"Startup initialization warning: {e}")

@app.get("/")
def read_root():
    return {"message": "Hello World from NetOps Backend!"}

@app.get("/api/status")
def status():
    return {"status": "ok", "service": "NetOps ML & RAG"}

@app.get("/api/topology")
async def get_network_topology():
    return manager.get_graph_data()

@app.post("/api/predict")
def predict(data: PredictRequest):
    status_prediction = ml_model.predict_node(
        data.cpu_usage,
        data.memory_usage,
        data.temperature,
        data.latency,
        data.packet_loss
    )
    return {"prediction": status_prediction}

@app.post("/api/chat")
def chat(data: ChatRequest):
    response_text = rag_system.query_chat(data.message)
    return {"reply": response_text}
