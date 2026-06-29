"""
audit_log.py — Tamper-evident audit log (SQLite, hash-chained rows).

Every RAG query, topology mutation, retrain trigger, and auth event is logged.
Each row hashes its own data + the previous row's hash (chain = tamper-evident).
"""

import sqlite3
import hashlib
import json
import time
from datetime import datetime

from config import AUDIT_DB_PATH


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(AUDIT_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp        TEXT    NOT NULL,
            username         TEXT    NOT NULL,
            role             TEXT    NOT NULL,
            event_type       TEXT    NOT NULL,
            node_id          TEXT,
            prompt           TEXT,
            response_summary TEXT,
            ip_address       TEXT,
            metadata         TEXT,
            prev_hash        TEXT,
            row_hash         TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def _last_hash() -> str:
    try:
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT row_hash FROM audit_log ORDER BY id DESC LIMIT 1"
            ).fetchone()
            return row["row_hash"] if row else "GENESIS"
    except Exception:
        return "GENESIS"


def _compute_hash(data: dict, prev_hash: str) -> str:
    payload = json.dumps({**data, "prev_hash": prev_hash}, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def log_event(
    username: str,
    role: str,
    event_type: str,
    node_id: str = None,
    prompt: str = None,
    response_summary: str = None,
    ip_address: str = None,
    metadata: dict = None,
):
    """
    event_type values:
      LOGIN_SUCCESS, LOGIN_FAILURE,
      RAG_QUERY, CONFIG_GENERATED,
      TOPOLOGY_ADD_NODE, TOPOLOGY_REMOVE_NODE,
      TOPOLOGY_ADD_EDGE, TOPOLOGY_REMOVE_EDGE,
      RETRAIN_TRIGGERED, FEEDBACK_SUBMITTED
    """
    ts = datetime.utcnow().isoformat()
    prev_hash = _last_hash()

    data = {
        "timestamp":        ts,
        "username":         username,
        "role":             role,
        "event_type":       event_type,
        "node_id":          node_id,
        "prompt":           prompt,
        "response_summary": (response_summary or "")[:500],
        "ip_address":       ip_address,
        "metadata":         json.dumps(metadata or {}),
    }

    row_hash = _compute_hash(data, prev_hash)

    try:
        with _get_conn() as conn:
            conn.execute("""
                INSERT INTO audit_log
                  (timestamp, username, role, event_type, node_id, prompt,
                   response_summary, ip_address, metadata, prev_hash, row_hash)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (
                data["timestamp"], data["username"], data["role"],
                data["event_type"], data["node_id"], data["prompt"],
                data["response_summary"], data["ip_address"],
                data["metadata"], prev_hash, row_hash
            ))
    except Exception as e:
        print(f"[audit] Write error: {e}")


def get_audit_log(limit: int = 100, event_type: str = None) -> list[dict]:
    try:
        with _get_conn() as conn:
            if event_type:
                rows = conn.execute(
                    "SELECT * FROM audit_log WHERE event_type=? ORDER BY id DESC LIMIT ?",
                    (event_type, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
                ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


def verify_integrity() -> dict:
    """Walk entire log and verify hash chain."""
    try:
        with _get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM audit_log ORDER BY id ASC"
            ).fetchall()

        prev_hash = "GENESIS"
        for row in rows:
            data = {
                "timestamp":        row["timestamp"],
                "username":         row["username"],
                "role":             row["role"],
                "event_type":       row["event_type"],
                "node_id":          row["node_id"],
                "prompt":           row["prompt"],
                "response_summary": row["response_summary"],
                "ip_address":       row["ip_address"],
                "metadata":         row["metadata"],
            }
            expected = _compute_hash(data, prev_hash)
            if expected != row["row_hash"]:
                return {"valid": False, "broken_at_id": row["id"]}
            prev_hash = row["row_hash"]

        return {"valid": True, "total_entries": len(rows)}
    except Exception as e:
        return {"valid": False, "error": str(e)}