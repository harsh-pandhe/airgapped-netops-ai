import os
import pandas as pd
import requests
import numpy as np
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import CrossEncoder

from graph_manager import manager
import ml_model  # <-- NEW: Importing the ML model to get live predictions!

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:3b"

# Global variables
vector_store = None
reranker = CrossEncoder('BAAI/bge-reranker-large', max_length=512)

# Simulated live state to match the frontend simulation in main.py
# Format: (cpu_usage, memory_usage, temperature, latency, packet_loss)
LIVE_STATE = {
    "RTR-001": (45.0, 60.0, 55.0, 20.0, 0.1),
    "RTR-002": (95.0, 95.0, 88.0, 150.0, 25.0),
    "SW-001": (20.0, 30.0, 40.0, 5.0, 0.0),
    "FW-001": (85.0, 70.0, 60.0, 50.0, 2.0)
}

def init_rag():
    global vector_store
    data_path = os.path.join(os.path.dirname(__file__), '../data/router_configs.csv')
    df = pd.read_csv(data_path)
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    
    docs = []
    for _, row in df.iterrows():
        chunks = text_splitter.split_text(row['config_text'])
        for i, chunk in enumerate(chunks):
            content = f"Node ID: {row['node_id']}\nDevice Type: {row['device_type']}\nConfig:\n{chunk}"
            meta = {"node_id": row['node_id'], "chunk_index": i + 1, "device_type": row['device_type']}
            docs.append(Document(page_content=content, metadata=meta))
            
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    db_path = os.path.join(os.path.dirname(__file__), "chroma_db")
    vector_store = Chroma.from_documents(docs, embeddings, persist_directory=db_path)
    print("RAG Pipeline: Chunking and ChromaDB initialized.")

def query_chat(prompt: str):
    if vector_store is None:
        init_rag()

    # 1. Retrieve & Rerank
    initial_results = vector_store.similarity_search(prompt, k=10)
    if not initial_results:
        return "No configuration found in vector database."
        
    scores = reranker.predict([[prompt, doc.page_content] for doc in initial_results])
    top_3_indices = np.argsort(scores)[::-1][:3]
    top_docs = [initial_results[i] for i in top_3_indices]

    context_blocks = []

    # --- NEW: Inject Live Telemetry from Track 3 ---
    telemetry_lines = ["--- LIVE NETWORK TELEMETRY CONTEXT ---"]
    
    # Find all unique nodes mentioned in the retrieved docs
    unique_nodes = list(set([doc.metadata.get('node_id', 'Unknown') for doc in top_docs]))
    
    for node in unique_nodes:
        if node in LIVE_STATE:
            vals = LIVE_STATE[node]
            # Ask the ML model for a prediction right now
            pred = ml_model.predict_node(*vals)
            
            status_label = "CRITICAL ANOMALY" if pred['anomaly'] else "NORMAL"
            ai_explanation = pred['explanation'] if pred['anomaly'] else "Operating within normal bounds."
            
            telemetry_lines.append(
                f"Node {node} -> CPU: {vals[0]}%, Latency: {vals[3]}ms | "
                f"Status: {status_label} | ML System Note: {ai_explanation}"
            )
            
    telemetry_lines.append("--- END TELEMETRY ---")
    context_blocks.append("\n".join(telemetry_lines))

    # --- Existing Logic: Topology & Configs ---
    primary_node = top_docs[0].metadata.get('node_id', 'Unknown')
    neighbors = manager.get_neighbor_details(primary_node)

    if neighbors:
        context_blocks.append(f"--- NETWORK TOPOLOGY CONTEXT: {primary_node} is connected to {', '.join(neighbors)} ---")

    for doc in top_docs:
        node = doc.metadata.get('node_id', 'Unknown')
        chunk = doc.metadata.get('chunk_index', '1')
        context_blocks.append(f"--- START SOURCE: {node} Config (Chunk {chunk}) ---\n{doc.page_content}\n--- END SOURCE ---")

    context = "\n\n".join(context_blocks)
    
    # 3. System Prompt Generation
    system_prompt = (
        "You are an expert Air-Gapped NetOps AI Copilot.\n"
        f"Context:\n{context}\n\n"
        f"Query: {prompt}\n\n"
        "INSTRUCTIONS:\n"
        "1. Use the provided context to answer the query. Prioritize the LIVE TELEMETRY when diagnosing issues.\n"
        "2. Accurately identify hardware (e.g., do not confuse Juniper with Cisco).\n"
        "3. CRITICAL: Every fact/config you cite MUST end with its source tag.\n"
        "4. Format: ... [Node ID Config (Chunk X)].\n"
        "Response:"
    )
    
    return call_ollama(system_prompt)

def call_ollama(system_prompt):
    try:
        payload = {"model": OLLAMA_MODEL, "prompt": system_prompt, "stream": False}
        response = requests.post(OLLAMA_URL, json=payload, timeout=180)
        return response.json().get("response", "Error processing request.")
    except Exception as e:
        return f"Error connecting to local LLM: {str(e)}"