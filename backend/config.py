"""
config.py — Central configuration for SENTINEL-MPLS.
All env vars override defaults at runtime.
"""
import os

# ── Telemetry ─────────────────────────────────────────────────────────────────
TELEMETRY_MODE = os.environ.get("TELEMETRY_MODE", "mock")   # "mock" | "snmp"
SNMP_COMMUNITY = os.environ.get("SNMP_COMMUNITY", "public")
SNMP_TARGETS   = os.environ.get("SNMP_TARGETS", "").split(",")  # comma-sep IPs
TELEMETRY_INTERVAL_S = float(os.environ.get("TELEMETRY_INTERVAL_S", "5"))

# ── Ollama ────────────────────────────────────────────────────────────────────
OLLAMA_URL   = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")

# ── Auth ──────────────────────────────────────────────────────────────────────
import secrets
JWT_SECRET        = os.environ.get("JWT_SECRET", secrets.token_hex(32))
JWT_ALGORITHM     = "HS256"
JWT_EXPIRY_HOURS  = int(os.environ.get("JWT_EXPIRY_HOURS", "8"))

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR        = os.path.dirname(__file__)
DATA_DIR        = os.path.join(BASE_DIR, "../data")
MODEL_DIR       = os.path.join(BASE_DIR, "models")
METRICS_DB_PATH = os.path.join(BASE_DIR, "metrics.db")
AUTH_DB_PATH    = os.path.join(BASE_DIR, "auth.db")
AUDIT_DB_PATH   = os.path.join(BASE_DIR, "audit.db")

# ── Demo ──────────────────────────────────────────────────────────────────────
DEMO_MODE = os.environ.get("DEMO_MODE", "false").lower() == "true"