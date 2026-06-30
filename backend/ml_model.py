"""
ml_model.py — IsolationForest anomaly detector with typed SHAP explanations.
Track 14: structured feature_impacts list, anomaly_score, unit map, SHAP log.
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import joblib
import shap
import os
import sqlite3
import time
from datetime import datetime
import warnings

from metrics_utils import track_performance, metrics
from config import DATA_DIR, MODEL_DIR, METRICS_DB_PATH

warnings.filterwarnings("ignore", category=UserWarning)

MODEL_PATH            = os.path.join(MODEL_DIR, "isolation_forest.joblib")
ACCUMULATED_LOGS_PATH = os.path.join(DATA_DIR, "accumulated_telemetry.csv")
FALSE_POSITIVE_LOG_PATH = os.path.join(DATA_DIR, "false_positives.csv")

FEATURE_NAMES = ['cpu_usage', 'memory_usage', 'temperature', 'latency', 'packet_loss']

FEATURE_UNITS = {
    'cpu_usage':    '%',
    'memory_usage': '%',
    'temperature':  '°C',
    'latency':      'ms',
    'packet_loss':  '%',
}


# ── SHAP log table ────────────────────────────────────────────────────────────

def _init_shap_table():
    conn = sqlite3.connect(METRICS_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS shap_explanations (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            event_ts      REAL    NOT NULL,
            node_id       TEXT,
            anomaly_score REAL,
            cpu_impact    REAL,
            memory_impact REAL,
            temp_impact   REAL,
            latency_impact REAL,
            loss_impact   REAL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS retrain_metadata (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            event_ts   REAL NOT NULL,
            status     TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

_init_shap_table()


def _log_shap(node_id: str, anomaly_score: float, impacts: list[dict]):
    try:
        imp_map = {i["feature"]: i["impact"] for i in (impacts or [])}
        conn = sqlite3.connect(METRICS_DB_PATH)
        conn.execute("""
            INSERT INTO shap_explanations
              (event_ts, node_id, anomaly_score,
               cpu_impact, memory_impact, temp_impact, latency_impact, loss_impact)
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            time.time(), node_id, anomaly_score,
            imp_map.get("cpu_usage"),    imp_map.get("memory_usage"),
            imp_map.get("temperature"),  imp_map.get("latency"),
            imp_map.get("packet_loss"),
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[shap_log] {e}")


def get_shap_history(node_id: str = None, limit: int = 20) -> list[dict]:
    try:
        conn = sqlite3.connect(METRICS_DB_PATH)
        conn.row_factory = sqlite3.Row
        if node_id:
            rows = conn.execute(
                "SELECT * FROM shap_explanations WHERE node_id=? ORDER BY id DESC LIMIT ?",
                (node_id, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM shap_explanations ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


# ── Detector ──────────────────────────────────────────────────────────────────

class TelemetryAnomalyDetector:
    def __init__(self, contamination=0.05, n_estimators=100):
        self.contamination  = contamination
        self.n_estimators   = n_estimators
        self.model = IsolationForest(
            n_estimators=n_estimators,
            contamination=contamination,
            random_state=42, n_jobs=-1
        )
        self.is_trained = False
        self.feature_names = FEATURE_NAMES

    def train(self, X, sample_weight=None):
        X_data = X.values if isinstance(X, pd.DataFrame) else X
        if sample_weight is not None:
            w = np.array(sample_weight)
            mn, mx = w.min(), w.max()
            repeats = (
                np.round(1 + 9 * (w - mn) / (mx - mn)).astype(int)
                if mx > mn else np.ones(len(w), dtype=int)
            )
            X_data = np.repeat(X_data, repeats, axis=0)
        self.model.fit(X_data)
        self.is_trained = True
        return self

    def predict(self, X):
        if not self.is_trained:
            raise ValueError("Model not trained.")
        X_data = X.values if isinstance(X, pd.DataFrame) else X
        return self.model.predict(X_data) == -1

    def score(self, X) -> float:
        X_data = X.values if isinstance(X, pd.DataFrame) else np.array(X)
        return float(self.model.decision_function(X_data)[0])


detector = TelemetryAnomalyDetector()


# ── Training ──────────────────────────────────────────────────────────────────

def train_model():
    data_path = os.path.join(DATA_DIR, "network_telemetry.csv")
    if os.path.exists(data_path):
        df = pd.read_csv(data_path)
        X  = df[FEATURE_NAMES]
        detector.train(X)
        os.makedirs(MODEL_DIR, exist_ok=True)
        joblib.dump(detector, MODEL_PATH)
    else:
        print(f"[ml_model] Training data not found: {data_path}")


def accumulate_telemetry_data(timestamp, cpu, memory, temp, latency, loss):
    new_data = pd.DataFrame([{
        'timestamp': timestamp, 'cpu_usage': cpu, 'memory_usage': memory,
        'temperature': temp, 'latency': latency, 'packet_loss': loss
    }])
    exists = os.path.exists(ACCUMULATED_LOGS_PATH)
    os.makedirs(os.path.dirname(ACCUMULATED_LOGS_PATH), exist_ok=True)
    new_data.to_csv(ACCUMULATED_LOGS_PATH, mode='a', header=not exists, index=False)


# ── SHAP ──────────────────────────────────────────────────────────────────────

def _get_shap_explanation(
    input_data: np.ndarray,
    raw_values: tuple,
) -> tuple[str, list[dict] | None]:
    """
    Returns (explanation_str, feature_impacts_list).
    feature_impacts_list is sorted by abs(impact) desc.
    Each entry: {"feature": str, "impact": float, "value": float, "unit": str}
    """
    try:
        explainer = shap.TreeExplainer(detector.model)
        shap_vals = explainer.shap_values(input_data)

        raw = shap_vals.values if hasattr(shap_vals, 'values') else shap_vals

        if isinstance(raw, np.ndarray):
            row = raw[0] if raw.ndim == 2 else raw
        elif isinstance(raw, list):
            row = np.array(raw[0]).flatten() if raw else np.zeros(len(FEATURE_NAMES))
        else:
            raise ValueError(f"Unexpected SHAP type: {type(raw)}")

        if len(row) != len(FEATURE_NAMES):
            raise ValueError(f"SHAP length mismatch: {len(row)}")

        impacts = []
        for i, feat in enumerate(FEATURE_NAMES):
            impacts.append({
                "feature": feat,
                "impact":  round(float(row[i]), 4),
                "value":   round(float(raw_values[i]), 2),
                "unit":    FEATURE_UNITS[feat],
            })

        impacts.sort(key=lambda x: abs(x["impact"]), reverse=True)
        top = impacts[0]
        explanation = (
            f"Anomaly detected. Primary driver: {top['feature']} "
            f"({top['value']}{top['unit']})"
        )
        return explanation, impacts

    except Exception as e:
        metrics["shap_fallback_count"] = metrics.get("shap_fallback_count", 0) + 1
        print(f"[SHAP WARNING] {type(e).__name__}: {e}")
        try:
            score = detector.score(input_data)
            return (
                f"Anomaly detected. SHAP unavailable ({type(e).__name__}): score-based fallback.",
                None
            )
        except Exception:
            return "Anomaly detected. Explanation unavailable.", None


# ── Predict ───────────────────────────────────────────────────────────────────

@track_performance("inference")
def predict_node(
    cpu: float, memory: float, temp: float,
    latency: float, loss: float,
    node_id: str = None,
) -> dict:
    global detector

    if not detector.is_trained:
        if os.path.exists(MODEL_PATH):
            detector = joblib.load(MODEL_PATH)
        else:
            train_model()

    ts         = datetime.now().isoformat()
    raw_values = (cpu, memory, temp, latency, loss)
    accumulate_telemetry_data(ts, cpu, memory, temp, latency, loss)

    input_data  = np.array([[cpu, memory, temp, latency, loss]])
    is_anomaly  = bool(detector.predict(input_data)[0])
    anomaly_score = detector.score(input_data)

    explanation   = "Traffic is normal."
    feature_impacts = None

    if is_anomaly:
        explanation, feature_impacts = _get_shap_explanation(input_data, raw_values)
        _log_shap(node_id or "unknown", anomaly_score, feature_impacts)

    return {
        "timestamp":      ts,
        "anomaly":        is_anomaly,
        "anomaly_score":  round(anomaly_score, 4),
        "explanation":    explanation,
        "feature_impacts": feature_impacts,
    }


# ── Retraining ────────────────────────────────────────────────────────────────

def run_daily_retraining_pipeline(window_days: int = 30) -> bool:
    if not os.path.exists(ACCUMULATED_LOGS_PATH):
        return False
    df = pd.read_csv(ACCUMULATED_LOGS_PATH)
    if len(df) < 10:
        return False

    X       = df[FEATURE_NAMES]
    weights = np.ones(len(df))

    if os.path.exists(FALSE_POSITIVE_LOG_PATH):
        fp_df = pd.read_csv(FALSE_POSITIVE_LOG_PATH)
        fp_ts = set(fp_df['timestamp'].astype(str))
        for i, ts in enumerate(df['timestamp'].astype(str)):
            if ts in fp_ts:
                weights[i] = 5.0

    new_det = TelemetryAnomalyDetector()
    new_det.train(X, sample_weight=weights)

    global detector
    detector = new_det
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(detector, MODEL_PATH)

    try:
        conn = sqlite3.connect(METRICS_DB_PATH)
        conn.execute(
            "INSERT INTO retrain_metadata (event_ts, status) VALUES (?, ?)",
            (time.time(), "success")
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

    return True


def flag_false_positive(timestamp: str) -> bool:
    if not os.path.exists(ACCUMULATED_LOGS_PATH):
        return False
    df         = pd.read_csv(ACCUMULATED_LOGS_PATH)
    target_row = df[df['timestamp'] == timestamp]
    if target_row.empty:
        return False

    fp_entry = target_row.copy()
    fp_entry['flagged_at'] = datetime.now().isoformat()
    exists = os.path.exists(FALSE_POSITIVE_LOG_PATH)
    os.makedirs(os.path.dirname(FALSE_POSITIVE_LOG_PATH), exist_ok=True)
    fp_entry.to_csv(FALSE_POSITIVE_LOG_PATH, mode='a', header=not exists, index=False)
    return True


def get_node_history(node_id: str, limit: int = 20) -> list[dict]:
    """Returns last N telemetry rows for a node from accumulated CSV."""
    if not os.path.exists(ACCUMULATED_LOGS_PATH):
        return []
    try:
        df = pd.read_csv(ACCUMULATED_LOGS_PATH)
        if 'node_id' in df.columns:
            df = df[df['node_id'] == node_id]
        return df.tail(limit).to_dict(orient='records')
    except Exception:
        return []


def get_last_retrain_timestamp() -> str | None:
    try:
        conn = sqlite3.connect(METRICS_DB_PATH)
        row  = conn.execute(
            "SELECT event_ts FROM retrain_metadata ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        if row:
            return datetime.fromtimestamp(row[0]).isoformat()
    except Exception:
        pass
    return None