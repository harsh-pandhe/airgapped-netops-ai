import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import joblib
import shap
import os
from datetime import datetime
import warnings
from metrics_utils import track_performance, metrics

warnings.filterwarnings("ignore", category=UserWarning)

MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "isolation_forest.joblib")
ACCUMULATED_LOGS_PATH = os.path.join(os.path.dirname(__file__), "../data/accumulated_telemetry.csv")
FALSE_POSITIVE_LOG_PATH = os.path.join(os.path.dirname(__file__), "../data/false_positives.csv")

FEATURE_NAMES = ['cpu_usage', 'memory_usage', 'temperature', 'latency', 'packet_loss']


class TelemetryAnomalyDetector:
    def __init__(self, contamination=0.05, n_estimators=100):
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=42,
            n_jobs=-1
        )
        self.is_trained = False
        self.feature_names = FEATURE_NAMES

    def train(self, X, sample_weight=None):
        X_data = X.values if isinstance(X, pd.DataFrame) else X
        # IsolationForest does not support sample_weight natively —
        # proportional oversampling is the correct approach (vs arbitrary 10x)
        if sample_weight is not None:
            weight_arr = np.array(sample_weight)
            min_w, max_w = weight_arr.min(), weight_arr.max()
            if max_w > min_w:
                repeats = np.round(1 + 9 * (weight_arr - min_w) / (max_w - min_w)).astype(int)
            else:
                repeats = np.ones(len(weight_arr), dtype=int)
            X_data = np.repeat(X_data, repeats, axis=0)
        self.model.fit(X_data)
        self.is_trained = True
        return self

    def predict(self, X):
        if not self.is_trained:
            raise ValueError("Model must be trained before running inference.")
        X_data = X.values if isinstance(X, pd.DataFrame) else X
        return self.model.predict(X_data) == -1


detector = TelemetryAnomalyDetector()


def train_model():
    data_path = os.path.join(os.path.dirname(__file__), '../data/network_telemetry.csv')
    if os.path.exists(data_path):
        df = pd.read_csv(data_path)
        X = df[FEATURE_NAMES]
        detector.train(X)
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump(detector, MODEL_PATH)
    else:
        print(f"Error: {data_path} not found.")


def accumulate_telemetry_data(timestamp, cpu, memory, temp, latency, loss):
    new_data = pd.DataFrame([{
        'timestamp': timestamp,
        'cpu_usage': cpu,
        'memory_usage': memory,
        'temperature': temp,
        'latency': latency,
        'packet_loss': loss
    }])
    file_exists = os.path.exists(ACCUMULATED_LOGS_PATH)
    os.makedirs(os.path.dirname(ACCUMULATED_LOGS_PATH), exist_ok=True)
    new_data.to_csv(ACCUMULATED_LOGS_PATH, mode='a', header=not file_exists, index=False)


def _get_shap_explanation(input_data: np.ndarray) -> tuple:
    try:
        if not hasattr(detector, 'model') or detector.model is None:
            raise ValueError("Model not available for SHAP.")

        explainer = shap.TreeExplainer(detector.model)
        shap_vals = explainer.shap_values(input_data)

        if hasattr(shap_vals, 'values'):
            raw = shap_vals.values
        else:
            raw = shap_vals

        if isinstance(raw, np.ndarray):
            row = raw[0] if raw.ndim == 2 else raw
        elif isinstance(raw, list):
            row = np.array(raw[0]).flatten() if raw else np.zeros(len(FEATURE_NAMES))
        else:
            raise ValueError(f"Unexpected SHAP type: {type(raw)}")

        if len(row) != len(FEATURE_NAMES):
            raise ValueError(f"SHAP length {len(row)} != {len(FEATURE_NAMES)}")

        impacts = dict(zip(FEATURE_NAMES, row))
        sorted_impacts = sorted(impacts.items(), key=lambda x: abs(x[1]), reverse=True)
        explanation = f"Anomaly detected. Primary driver: {sorted_impacts[0][0]}"
        return explanation, {k: float(v) for k, v in sorted_impacts}

    except Exception as e:
        try:
            score = float(detector.model.decision_function(input_data)[0])
            return (
                f"Anomaly detected. SHAP unavailable ({type(e).__name__}): score-based fallback.",
                {"_shap_error": str(e), "_anomaly_score": score}
            )
        except Exception:
            return "Anomaly detected. Explanation unavailable.", None


@track_performance("inference")
def predict_node(cpu: float, memory: float, temp: float, latency: float, loss: float):
    global detector

    if not detector.is_trained:
        if os.path.exists(MODEL_PATH):
            detector = joblib.load(MODEL_PATH)
        else:
            train_model()

    current_timestamp = datetime.now().isoformat()
    accumulate_telemetry_data(current_timestamp, cpu, memory, temp, latency, loss)

    input_data = np.array([[cpu, memory, temp, latency, loss]])
    is_anomaly = bool(detector.predict(input_data)[0])

    explanation = "Traffic is normal."
    raw_impacts = None

    if is_anomaly:
        explanation, raw_impacts = _get_shap_explanation(input_data)

    return {
        "timestamp": current_timestamp,
        "anomaly": is_anomaly,
        "explanation": explanation,
        "feature_impacts": raw_impacts
    }


def run_daily_retraining_pipeline(window_days=30):
    """
    Retrain on accumulated telemetry with false-positive upweighting.
    False positives are stored in a separate log — original data untouched.
    """
    if not os.path.exists(ACCUMULATED_LOGS_PATH):
        return False
    df = pd.read_csv(ACCUMULATED_LOGS_PATH)
    if len(df) < 10:
        return False

    X = df[FEATURE_NAMES]
    weights = np.ones(len(df))

    if os.path.exists(FALSE_POSITIVE_LOG_PATH):
        fp_df = pd.read_csv(FALSE_POSITIVE_LOG_PATH)
        fp_timestamps = set(fp_df['timestamp'].astype(str))
        for i, ts in enumerate(df['timestamp'].astype(str)):
            if ts in fp_timestamps:
                weights[i] = 5.0  # tunable upweight factor

    new_detector = TelemetryAnomalyDetector()
    new_detector.train(X, sample_weight=weights)

    global detector
    detector = new_detector
    joblib.dump(detector, MODEL_PATH)
    return True


def flag_false_positive(timestamp: str):
    """
    Appends the flagged sample to false_positives.csv.
    Does NOT mutate accumulated_telemetry.csv.
    Retraining pipeline reads fp log and upweights those rows.
    """
    if not os.path.exists(ACCUMULATED_LOGS_PATH):
        return False
    df = pd.read_csv(ACCUMULATED_LOGS_PATH)
    target_row = df[df['timestamp'] == timestamp]
    if target_row.empty:
        return False

    fp_entry = target_row.copy()
    fp_entry['flagged_at'] = datetime.now().isoformat()
    file_exists = os.path.exists(FALSE_POSITIVE_LOG_PATH)
    os.makedirs(os.path.dirname(FALSE_POSITIVE_LOG_PATH), exist_ok=True)
    fp_entry.to_csv(FALSE_POSITIVE_LOG_PATH, mode='a', header=not file_exists, index=False)
    return True