"""
rag_system.py — RAG pipeline with two-mode prompting (Track 15) and domain filtering.
Mode A: diagnostic  — cited explanation + 3 remediation steps
Mode B: mitigation  — runnable Cisco IOS / JunOS config blocks
"""

import os
import sqlite3
import time
import re
from typing import Literal

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
from metrics_utils import track_performance, record_tokens
from config import OLLAMA_URL, OLLAMA_MODEL, METRICS_DB_PATH

vector_store = None
reranker     = CrossEncoder('BAAI/bge-reranker-large', max_length=512)

# ── Query log table ───────────────────────────────────────────────────────────

def _init_query_log():
    conn = sqlite3.connect(METRICS_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS query_log (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            event_ts       REAL,
            intent         TEXT,
            had_code_block INTEGER,
            prompt_len     INTEGER,
            response_len   INTEGER
        )
    """)
    conn.commit()
    conn.close()

_init_query_log()


def _log_query(intent: str, had_code_block: bool, prompt_len: int, response_len: int):
    try:
        conn = sqlite3.connect(METRICS_DB_PATH)
        conn.execute(
            "INSERT INTO query_log (event_ts, intent, had_code_block, prompt_len, response_len)"
            " VALUES (?,?,?,?,?)",
            (time.time(), intent, int(had_code_block), prompt_len, response_len)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[query_log] {e}")


# ── Intent classifier ─────────────────────────────────────────────────────────

MITIGATION_KEYWORDS = {
    "fix", "mitigate", "configure", "apply", "remediate",
    "resolve", "patch", "deploy", "set", "change", "update",
    "generate", "create", "write", "commands", "config",
}

def classify_intent(prompt: str) -> Literal["diagnostic", "mitigation"]:
    tokens = set(prompt.lower().split())
    return "mitigation" if tokens & MITIGATION_KEYWORDS else "diagnostic"


# ── RAG init ──────────────────────────────────────────────────────────────────

def init_rag():
    global vector_store
    data_path = os.path.join(os.path.dirname(__file__), '../data/router_configs.csv')
    df        = pd.read_csv(data_path)
    splitter  = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs      = []
    for _, row in df.iterrows():
        chunks = splitter.split_text(row['config_text'])
        for i, chunk in enumerate(chunks):
            content = (
                f"Node ID: {row['node_id']}\n"
                f"Device Type: {row['device_type']}\n"
                f"Config:\n{chunk}"
            )
            meta = {
                "node_id":     row['node_id'],
                "chunk_index": i + 1,
                "device_type": row['device_type'],
            }
            docs.append(Document(page_content=content, metadata=meta))

    embeddings  = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    db_path     = os.path.join(os.path.dirname(__file__), "chroma_db")
    vector_store = Chroma.from_documents(docs, embeddings, persist_directory=db_path)


# ── Live telemetry ────────────────────────────────────────────────────────────

def _get_live_state() -> dict:
    """Read from module-level engine (avoids HTTP roundtrip)."""
    try:
        from telemetry_poller import engine
        return engine.get_state()
    except Exception:
        return {}


# ── System prompts ────────────────────────────────────────────────────────────

def _build_diagnostic_prompt(context: str, citation_instructions: str, prompt: str) -> str:
    return f"""You are an ISRO Network Operations Engineer with 15 years of Cisco IOS and Juniper JunOS experience.
You have access to live telemetry and device configurations for an air-gapped network.

AVAILABLE SOURCES:
{citation_instructions}

CONTEXT:
{context}

QUERY: {prompt}

RULES:
1. Cite every factual claim using [Node ID Config (Chunk N)] format.
2. State the anomaly cause in ONE sentence. Then list affected metrics with values.
3. Recommend exactly 3 remediation steps, each starting with an action verb.
4. End with a "Confidence:" line: High / Medium / Low based on telemetry clarity.
5. End with a "Sources Used:" section listing every citation referenced.

RESPONSE:"""


def _build_mitigation_prompt(context: str, citation_instructions: str, prompt: str) -> str:
    return f"""You are an ISRO Network Operations Engineer. You MUST output runnable Cisco IOS or Juniper JunOS commands.

AVAILABLE SOURCES:
{citation_instructions}

CONTEXT:
{context}

QUERY: {prompt}

RULES:
1. Output commands ONLY inside markdown code blocks tagged with the OS: ```cisco-ios or ```junos
2. Use the EXACT IP addresses and interface names from the configuration context above.
3. Include interface shutdown/no shutdown steps if rebooting an interface.
4. Add a comment line (!) before each logical section explaining what it does.
5. After the code block, output ONE line: "⚠ Apply on: [node_id] via console or SSH to [ip]"
6. Do NOT add prose after the code block. Commands only.

RESPONSE:"""


# ── Main chat function ────────────────────────────────────────────────────────

@track_performance("retrieval")
def query_chat(prompt: str, user=None) -> str:
    if vector_store is None:
        init_rag()

    # Domain filter for ChromaDB
    where_filter = None
    if user and "*" not in user.domains:
        from auth import DEVICE_DOMAINS
        permitted = [nid for nid, dom in DEVICE_DOMAINS.items() if dom in user.domains]
        if permitted:
            where_filter = {"node_id": {"$in": permitted}}

    initial_results = vector_store.similarity_search(prompt, k=10, filter=where_filter)
    if not initial_results:
        return "No configuration found for your permitted domains."

    scores       = reranker.predict([[prompt, doc.page_content] for doc in initial_results])
    top_3_idx    = np.argsort(scores)[::-1][:3]
    top_docs     = [initial_results[i] for i in top_3_idx]
    top_scores   = [float(scores[i]) for i in top_3_idx]

    # Log reranker scores to metrics DB
    _log_reranker_scores(top_scores)

    live_state     = _get_live_state()
    context_blocks = []

    # Telemetry block
    telemetry_lines = ["--- LIVE NETWORK TELEMETRY CONTEXT ---"]
    unique_nodes    = list(set(doc.metadata.get('node_id', 'Unknown') for doc in top_docs))
    for node in unique_nodes:
        if node in live_state:
            v    = live_state[node]
            pred = ml_model.predict_node(v["cpu"], v["memory"], v["temperature"],
                                         v["latency"], v["packet_loss"], node_id=node)
            status = "CRITICAL ANOMALY" if pred['anomaly'] else "NORMAL"
            telemetry_lines.append(
                f"Node {node} -> CPU: {v['cpu']}%, Latency: {v['latency']}ms | Status: {status}"
            )
    telemetry_lines.append("--- END TELEMETRY ---")
    context_blocks.append("\n".join(telemetry_lines))

    # Topology block
    primary_node = top_docs[0].metadata.get('node_id', 'Unknown')
    neighbors    = manager.get_neighbors(primary_node)
    if neighbors:
        context_blocks.append(
            f"--- TOPOLOGY: {primary_node} connects to {', '.join(neighbors)} ---"
        )

    # Source blocks
    citation_map = []
    for doc in top_docs:
        node  = doc.metadata.get('node_id', 'Unknown')
        chunk = doc.metadata.get('chunk_index', '1')
        label = f"{node} Config (Chunk {chunk})"
        citation_map.append(label)
        context_blocks.append(
            f"--- START SOURCE: {label} ---\n{doc.page_content}\n--- END SOURCE ---"
        )

    context               = "\n\n".join(context_blocks)
    citation_instructions = "\n".join(f"  [{i+1}] {lbl}" for i, lbl in enumerate(citation_map))

    # Intent classification → select prompt mode
    intent = classify_intent(prompt)
    if intent == "mitigation":
        system_prompt = _build_mitigation_prompt(context, citation_instructions, prompt)
    else:
        system_prompt = _build_diagnostic_prompt(context, citation_instructions, prompt)

    response = _call_ollama(system_prompt)

    # Validation: mitigation mode must contain a code block
    has_code_block = bool(
        re.search(r'```(?:cisco-ios|junos)', response, re.IGNORECASE)
    )
    if intent == "mitigation" and not has_code_block:
        response += (
            "\n\n⚠ Model did not generate config commands. "
            "Try rephrasing as: 'Generate Cisco IOS commands to fix [issue] on [node].'"
        )

    record_tokens(response)
    _log_query(intent, has_code_block, len(prompt), len(response))

    return response


def _log_reranker_scores(scores: list[float]):
    try:
        conn = sqlite3.connect(METRICS_DB_PATH)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reranker_scores (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                event_ts REAL,
                score1   REAL,
                score2   REAL,
                score3   REAL
            )
        """)
        padded = (scores + [None, None, None])[:3]
        conn.execute(
            "INSERT INTO reranker_scores (event_ts, score1, score2, score3) VALUES (?,?,?,?)",
            (time.time(), *padded)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def _call_ollama(system_prompt: str) -> str:
    try:
        payload  = {"model": OLLAMA_MODEL, "prompt": system_prompt, "stream": False}
        response = requests.post(OLLAMA_URL, json=payload, timeout=180)
        return response.json().get("response", "Error.")
    except Exception as e:
        return f"Error: {str(e)}"