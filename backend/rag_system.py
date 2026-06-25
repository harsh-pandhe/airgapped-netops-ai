import os
import pandas as pd
import requests
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document

OLLAMA_URL = "http://localhost:11434/api/generate"
# Using qwen3:14b as discovered in your local environment instead of phi-3
OLLAMA_MODEL = "qwen3:14b" 

vector_store = None

def init_rag():
    global vector_store
    data_path = os.path.join(os.path.dirname(__file__), '../data/router_configs.csv')
    df = pd.read_csv(data_path)
    
    docs = []
    for _, row in df.iterrows():
        content = f"Node ID: {row['node_id']}\nDevice Type: {row['device_type']}\nIP Address: {row['ip_address']}\nConfig:\n{row['config_text']}"
        docs.append(Document(page_content=content, metadata={"node_id": row['node_id']}))
        
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    db_path = os.path.join(os.path.dirname(__file__), "chroma_db")
    vector_store = Chroma.from_documents(docs, embeddings, persist_directory=db_path)
    print("RAG Pipeline initialized with ChromaDB.")

def query_chat(prompt: str):
    if vector_store is None:
        init_rag()
        
    results = vector_store.similarity_search(prompt, k=2)
    context = "\n\n".join([doc.page_content for doc in results])
    
    system_prompt = (
        "You are an expert, strict network engineer. You are managing an air-gapped network.\n"
        "Use the provided configuration context to answer the user's question.\n"
        "If they ask to 'fix' a failing node or update a configuration, output precise Cisco or Juniper configuration commands in markdown format.\n"
        "If the user asks a non-network related question, politely decline and remind them you are a NetOps assistant.\n\n"
        f"Context from ChromaDB:\n{context}\n\n"
        f"User Query: {prompt}\n\n"
        "Response:"
    )
    
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": system_prompt,
        "stream": False
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()
        return response.json().get("response", "Error: No response field in JSON.")
    except Exception as e:
        return f"Error communicating with local Ollama ({OLLAMA_MODEL}): {str(e)}"
