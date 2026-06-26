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

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:3b"

# Global variables
vector_store = None
reranker = CrossEncoder('BAAI/bge-reranker-large', max_length=512)

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
            meta = {"node_id": row['node_id'], "chunk_index": i + 1}
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
        return "No configuration found."
        
    scores = reranker.predict([[prompt, doc.page_content] for doc in initial_results])
    top_3_indices = np.argsort(scores)[::-1][:3]
    top_docs = [initial_results[i] for i in top_3_indices]

    # 2. Graph-Aware Logic
    context_blocks = []
    primary_node = top_docs[0].metadata.get('node_id', 'Unknown')
    neighbors = manager.get_neighbor_details(primary_node)

    if neighbors:
        context_blocks.append(f"--- NETWORK TOPOLOGY CONTEXT: {primary_node} is connected to {', '.join(neighbors)} ---")

    for doc in top_docs:
        node = doc.metadata.get('node_id', 'Unknown')
        chunk = doc.metadata.get('chunk_index', '1')
        context_blocks.append(f"--- START SOURCE: {node} Config (Chunk {chunk}) ---\n{doc.page_content}\n--- END SOURCE ---")

    context = "\n\n".join(context_blocks)
    
    system_prompt = (
        "You are an expert Air-Gapped NetOps AI Copilot.\n"
        f"Context:\n{context}\n\n"
        f"Query: {prompt}\n\n"
        "INSTRUCTIONS:\n"
        "1. Use the provided context to answer the query.\n"
        "2. CRITICAL: Every fact/config you cite MUST end with its source tag.\n"
        "3. Format: ... [Node ID Config (Chunk X)].\n"
        "Response:"
    )
    
    return call_ollama(system_prompt)

def call_ollama(system_prompt):
    try:
        payload = {"model": OLLAMA_MODEL, "prompt": system_prompt, "stream": False}
        response = requests.post(OLLAMA_URL, json=payload, timeout=180)
        return response.json().get("response", "Error.")
    except Exception as e:
        return f"Error: {str(e)}"