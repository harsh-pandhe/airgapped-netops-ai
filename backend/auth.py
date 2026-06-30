"""
auth.py — Local JWT Authentication + RBAC Engine

Roles:
  read_only_operator : view telemetry, query RAG — own domains only
  network_architect  : full access, all domains, CRUD, retrain, audit log

Device Domains:
  core : RTR-001, RTR-002
  edge : FW-001
  dmz  : SW-001
"""

import os
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

from config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRY_HOURS, AUTH_DB_PATH, DEMO_MODE

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# ── Domain map ────────────────────────────────────────────────────────────────

DEVICE_DOMAINS: dict[str, str] = {
    "RTR-001": "core",
    "RTR-002": "core",
    "FW-001":  "edge",
    "SW-001":  "dmz",
}

# ── Role → permissions ────────────────────────────────────────────────────────

ROLE_PERMISSIONS: dict[str, dict] = {
    "read_only_operator": {
        "can_query_rag":       True,
        "can_view_telemetry":  True,
        "can_crud_topology":   False,
        "can_trigger_retrain": False,
        "can_view_audit_log":  False,
    },
    "network_architect": {
        "can_query_rag":       True,
        "can_view_telemetry":  True,
        "can_crud_topology":   True,
        "can_trigger_retrain": True,
        "can_view_audit_log":  True,
    },
}

# ── DB ────────────────────────────────────────────────────────────────────────

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(AUTH_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username      TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            role          TEXT NOT NULL,
            domains       TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify(password: str, stored_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), stored_hash.encode())
    except (ValueError, TypeError):
        return False


def seed_default_users():
    """Seed demo accounts. Only runs when DEMO_MODE=true, or when explicit
    DEFAULT_OPERATOR_PASSWORD / DEFAULT_ARCHITECT_PASSWORD env vars are set.
    Refuses to seed hardcoded credentials in a non-demo deployment."""
    op_pw   = os.environ.get("DEFAULT_OPERATOR_PASSWORD")
    arch_pw = os.environ.get("DEFAULT_ARCHITECT_PASSWORD")

    if DEMO_MODE:
        op_pw   = op_pw   or "operator123"
        arch_pw = arch_pw or "architect123"
    elif not (op_pw and arch_pw):
        # Non-demo and no explicit passwords provided — do not seed.
        return

    defaults = [
        ("operator",  op_pw,   "read_only_operator", "core,dmz"),
        ("architect", arch_pw, "network_architect",  "*"),
    ]
    with _get_conn() as conn:
        for username, pw, role, domains in defaults:
            if not conn.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
                conn.execute(
                    "INSERT INTO users VALUES (?,?,?,?)",
                    (username, _hash(pw), role, domains)
                )


# ── Token models ──────────────────────────────────────────────────────────────

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    domains: list[str]


class TokenData(BaseModel):
    username: str
    role: str
    domains: list[str]


# ── Auth helpers ──────────────────────────────────────────────────────────────

def authenticate_user(username: str, password: str) -> Optional[sqlite3.Row]:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        ).fetchone()
    if row and _verify(password, row["password_hash"]):
        return row
    return None


def create_access_token(username: str, role: str, domains: list[str]) -> str:
    payload = {
        "sub": username,
        "role": role,
        "domains": domains,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username = payload.get("sub")
        role     = payload.get("role")
        domains  = payload.get("domains", [])
        if not username or not role:
            raise exc
        return TokenData(username=username, role=role, domains=domains)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise exc


# ── Permission guards ─────────────────────────────────────────────────────────

def require_permission(permission: str):
    async def guard(user: TokenData = Depends(get_current_user)) -> TokenData:
        if not ROLE_PERMISSIONS.get(user.role, {}).get(permission, False):
            raise HTTPException(
                status_code=403,
                detail=f"Role '{user.role}' lacks permission '{permission}'"
            )
        return user
    return guard


def check_node_access(node_id: str, user: TokenData):
    if "*" in user.domains:
        return
    domain = DEVICE_DOMAINS.get(node_id)
    if domain and domain not in user.domains:
        raise HTTPException(
            status_code=403,
            detail=f"Node {node_id} is in domain '{domain}'; "
                   f"your permitted domains: {user.domains}"
        )


def filter_nodes_by_domain(node_ids: list[str], user: TokenData) -> list[str]:
    if "*" in user.domains:
        return node_ids
    return [n for n in node_ids if DEVICE_DOMAINS.get(n) in user.domains]