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
import ml_model
from metrics_utils import track_performance, metrics, record_tokens

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:3b"

vector_store = None
reranker = CrossEncoder('BAAI/bge-reranker-large', max_length=512)

# --- Dynamic telemetry fetcher ---
# Replace this function body with a real SNMP/API call when available.
# Returns dict: { node_id: (cpu, memory, temp, latency, packet_loss) }
STATIC_TELEMETRY_FALLBACK = {
    "RTR-001": (45.0, 60.0, 55.0, 20.0, 0.1),
    "RTR-002": (95.0, 95.0, 88.0, 150.0, 25.0),
    "SW-001":  (20.0, 30.0, 40.0, 5.0, 0.0),
    "FW-001":  (85.0, 70.0, 60.0, 50.0, 2.0),
}

def get_live_telemetry() -> dict:
    """
    Fetches raw telemetry from /api/live-state.
    Falls back to static values if the endpoint is unreachable.
    Swap the endpoint URL for a real SNMP poller when available.
    """
    try:
        response = requests.get("http://localhost:8000/api/live-state", timeout=5)
        if response.status_code == 200:
            raw = response.json()
            result = {}
            for node_id, vals in raw.items():
                result[node_id] = (
                    vals["cpu"],
                    vals["memory"],
                    vals["temperature"],
                    vals["latency"],
                    vals["packet_loss"],
                )
            if result:
                return result
    except Exception:
        pass

    return STATIC_TELEMETRY_FALLBACK


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


@track_performance("retrieval")
def query_chat(prompt: str):
    if vector_store is None:
        init_rag()

    initial_results = vector_store.similarity_search(prompt, k=10)
    if not initial_results:
        return "No configuration found."

    scores = reranker.predict([[prompt, doc.page_content] for doc in initial_results])
    top_3_indices = np.argsort(scores)[::-1][:3]
    top_docs = [initial_results[i] for i in top_3_indices]

    # --- Dynamic telemetry (fetched fresh per query) ---
    live_state = get_live_telemetry()

    context_blocks = []
    telemetry_lines = ["--- LIVE NETWORK TELEMETRY CONTEXT ---"]
    unique_nodes = list(set([doc.metadata.get('node_id', 'Unknown') for doc in top_docs]))

    for node in unique_nodes:
        if node in live_state:
            vals = live_state[node]
            pred = ml_model.predict_node(*vals)
            status_label = "CRITICAL ANOMALY" if pred['anomaly'] else "NORMAL"
            telemetry_lines.append(
                f"Node {node} -> CPU: {vals[0]}%, Latency: {vals[3]}ms | Status: {status_label}"
            )

    telemetry_lines.append("--- END TELEMETRY ---")
    context_blocks.append("\n".join(telemetry_lines))

    # --- Topology context (uses get_neighbors, not the deleted duplicate) ---
    primary_node = top_docs[0].metadata.get('node_id', 'Unknown')
    neighbors = manager.get_neighbors(primary_node)
    if neighbors:
        context_blocks.append(
            f"--- TOPOLOGY: {primary_node} connects to {', '.join(neighbors)} ---"
        )

    # --- Source blocks with citation-compatible labels ---
    citation_map = []
    for doc in top_docs:
        node = doc.metadata.get('node_id', 'Unknown')
        chunk = doc.metadata.get('chunk_index', '1')
        citation_label = f"{node} Config (Chunk {chunk})"
        citation_map.append(citation_label)
        context_blocks.append(
            f"--- START SOURCE: {citation_label} ---\n{doc.page_content}\n--- END SOURCE ---"
        )

    context = "\n\n".join(context_blocks)

    # --- System prompt: strictly enforces citation format ---
    citation_instructions = "\n".join(
        [f"  [{i+1}] {label}" for i, label in enumerate(citation_map)]
    )

    system_prompt = f"""You are a network operations AI assistant with access to live telemetry and device configurations.

AVAILABLE SOURCES:
{citation_instructions}

CONTEXT:
{context}

QUERY: {prompt}

STRICT INSTRUCTIONS:
1. You MUST cite every specific claim using the format [Node ID Config (Chunk X)] where Node ID and X match the sources above.
   Example: "RTR-001 has BGP configured on interface GigabitEthernet0/0 [RTR-001 Config (Chunk 2)]."
2. Prioritize LIVE TELEMETRY when describing node status.
3. If a fact comes from topology context, note the connected nodes explicitly.
4. Do NOT make claims without a citation from the sources above.
5. End your response with a "Sources Used:" section listing every citation you referenced.

RESPONSE:"""

    response = call_ollama(system_prompt)

    record_tokens(response)

    return response


def call_ollama(system_prompt):
    try:
        payload = {"model": OLLAMA_MODEL, "prompt": system_prompt, "stream": False}
        response = requests.post(OLLAMA_URL, json=payload, timeout=180)
        return response.json().get("response", "Error.")
    except Exception as e:
        return f"Error: {str(e)}"