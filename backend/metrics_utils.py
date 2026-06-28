import time
import sqlite3
import os
from functools import wraps

try:
    from transformers import AutoTokenizer
    _tokenizer = AutoTokenizer.from_pretrained("gpt2")  # fast, local, no network
    def count_tokens(text: str) -> int:
        return len(_tokenizer.encode(text, add_special_tokens=False))
except Exception:
    # Fallback if transformers not available
    def count_tokens(text: str) -> int:
        return len(text) // 4

DB_PATH = os.path.join(os.path.dirname(__file__), "metrics.db")

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS performance_events (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            event_ts  REAL    NOT NULL,
            metric    TEXT    NOT NULL,
            value_ms  REAL    NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS token_counts (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            event_ts REAL NOT NULL,
            tokens   INTEGER NOT NULL
        )
    """)
    conn.commit()
    return conn


def _write_event(metric: str, value_ms: float):
    try:
        with _get_conn() as conn:
            conn.execute(
                "INSERT INTO performance_events (event_ts, metric, value_ms) VALUES (?, ?, ?)",
                (time.time(), metric, value_ms)
            )
    except Exception as e:
        print(f"[metrics] DB write error: {e}")


def _write_tokens(n: int):
    try:
        with _get_conn() as conn:
            conn.execute(
                "INSERT INTO token_counts (event_ts, tokens) VALUES (?, ?)",
                (time.time(), n)
            )
    except Exception as e:
        print(f"[metrics] DB token write error: {e}")


def _read_avg(metric: str) -> float:
    try:
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT AVG(value_ms) FROM performance_events WHERE metric = ?",
                (metric,)
            ).fetchone()
            return row[0] or 0.0
    except Exception:
        return 0.0


def _read_total_tokens() -> int:
    try:
        with _get_conn() as conn:
            row = conn.execute("SELECT SUM(tokens) FROM token_counts").fetchone()
            return row[0] or 0
    except Exception:
        return 0


# --- In-memory mirror (keeps existing callers working) ---
metrics = {
    "inference_times": [],
    "retrieval_durations": [],
    "total_tokens_generated": 0,   # legacy field — use get_total_tokens() for accurate value
}


def get_avg_inference_ms() -> float:
    return _read_avg("inference")

def get_avg_retrieval_ms() -> float:
    return _read_avg("retrieval")

def get_total_tokens() -> int:
    return _read_total_tokens()


def record_tokens(text: str):
    """Call this instead of the len(response)//4 hack."""
    n = count_tokens(text)
    metrics["total_tokens_generated"] += n   # keep in-memory mirror in sync
    _write_tokens(n)


def track_performance(metric_type: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            duration = (time.perf_counter() - start) * 1000  # ms

            if metric_type == "inference":
                metrics["inference_times"].append(duration)
                _write_event("inference", duration)
            elif metric_type == "retrieval":
                metrics["retrieval_durations"].append(duration)
                _write_event("retrieval", duration)

            return result
        return wrapper
    return decorator