# Air-Gapped NetOps AI

An intelligent, secure, and fully local Network Operations (NetOps) dashboard and AI assistant designed to run in air-gapped environments. It combines live network telemetry analysis using local machine learning with a local Retrieval-Augmented Generation (RAG) assistant for secure, conversational troubleshooting and configuration generation.

## Features

- **Local ML Predictions**: A local Random Forest classifier predicts network node statuses (Healthy, Warning, Critical, Failed) based on real-time telemetry (CPU, Memory, Temp, Latency, Packet Loss) without sending data to external APIs.
- **Local RAG Copilot**: A secure local AI assistant powered by **Ollama (`qwen3:14b`)** and **ChromaDB** using **HuggingFace Embeddings (`all-MiniLM-L6-v2`)**. It parses local router/switch configurations to answer troubleshooting queries and output precise configuration commands (Cisco, Juniper).
- **Responsive Dashboard**: Built with **React**, **TypeScript**, **Vite**, and **Tailwind CSS v4** featuring modern dark-mode aesthetics, status trackers, and interactive terminal interfaces.
- **Air-Gapped First**: Designed from the ground up to operate with zero internet connectivity. No telemetry, configuration files, or chat queries leave the host machine.

---

## Project Structure

```text
airgapped-netops-ai/
├── backend/                  # FastAPI Backend
│   ├── main.py               # API endpoints & startup orchestration
│   ├── ml_model.py           # Random Forest node classifier logic
│   ├── rag_system.py         # ChromaDB similarity search & Ollama interface
│   ├── requirements.txt      # Python dependencies
│   └── data/                 # Local network datasets (CSV)
├── frontend/                 # Vite + React + TS Frontend
│   ├── src/                  # React source files (App, styles)
│   ├── package.json          # Node dependencies
│   └── vite.config.ts        # Vite build & plugin configuration
└── README.md                 # Project documentation
```

---

## Prerequisites

Ensure you have the following installed on your local system:
- **Python**: version 3.10 or higher
- **Node.js**: version 18 or higher (with npm)
- **Ollama**: Running locally with the `qwen3:14b` model pulled:
  ```bash
  ollama pull qwen3:14b
  ```

---

## Getting Started

### 1. Set Up and Run the Backend

Navigate to the `backend` directory:
```bash
cd backend
```

Create a virtual environment and activate it:
```bash
python3 -m venv venv
source venv/bin/activate
```

Install the required Python dependencies:
```bash
pip install -r requirements.txt
```

Start the FastAPI backend server:
```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
*The ML model is automatically trained and the RAG pipeline is initialized with the local configuration dataset on startup.*

### 2. Set Up and Run the Frontend

Open a new terminal window/tab and navigate to the `frontend` directory:
```bash
cd frontend
```

Install the frontend dependencies:
```bash
npm install
```

Start the Vite development server:
```bash
npm run dev
```
Open `http://localhost:5173/` in your web browser to access the dashboard.

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.
