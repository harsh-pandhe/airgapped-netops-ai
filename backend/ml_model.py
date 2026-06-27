import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import joblib
import shap
import os
from datetime import datetime
import warnings


warnings.filterwarnings("ignore", category=UserWarning)

MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "isolation_forest.joblib")
ACCUMULATED_LOGS_PATH = os.path.join(os.path.dirname(__file__), "../data/accumulated_telemetry.csv")

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
        self.feature_names = ['cpu_usage', 'memory_usage', 'temperature', 'latency', 'packet_loss']

    def train(self, X):
        X_data = X.values if isinstance(X, pd.DataFrame) else X
        self.model.fit(X_data)
        self.is_trained = True
        return self

    def predict(self, X):
        if not self.is_trained:
            raise ValueError("Model must be trained before running inference.")
        X_data = X.values if isinstance(X, pd.DataFrame) else X
        predictions = self.model.predict(X_data)
        return predictions == -1

# Global instance
detector = TelemetryAnomalyDetector()

def train_model():
    """Loads CSV data and trains the unsupervised Isolation Forest."""
    data_path = os.path.join(os.path.dirname(__file__), '../data/network_telemetry.csv')
    if os.path.exists(data_path):
        df = pd.read_csv(data_path)
        X = df[['cpu_usage', 'memory_usage', 'temperature', 'latency', 'packet_loss']]
        detector.train(X)
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump(detector, MODEL_PATH)
        print("Isolation Forest trained successfully.")
    else:
        print(f"Error: {data_path} not found.")

def accumulate_telemetry_data(timestamp, cpu, memory, temp, latency, loss):
    """Appends streaming telemetry data to a local CSV file for retraining."""
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

def predict_node(cpu: float, memory: float, temp: float, latency: float, loss: float):
    """Predicts anomalies and uses SHAP to explain the root cause."""
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
        explainer = shap.TreeExplainer(detector.model)
        shap_vals = explainer.shap_values(input_data)
        
        features = ['cpu_usage', 'memory_usage', 'temperature', 'latency', 'packet_loss']
        impacts = dict(zip(features, shap_vals[0]))
        sorted_impacts = sorted(impacts.items(), key=lambda item: abs(item[1]), reverse=True)
        
        top_feature = sorted_impacts[0][0]
        explanation = f"Anomaly detected. Primary driver: {top_feature}"
        raw_impacts = {k: float(v) for k, v in sorted_impacts}
        
    return {
        "timestamp": current_timestamp,  
        "anomaly": is_anomaly,
        "explanation": explanation,
        "feature_impacts": raw_impacts
    }

def run_daily_retraining_pipeline(window_days=30):
    """Retrains the model using recently accumulated telemetry."""
    if not os.path.exists(ACCUMULATED_LOGS_PATH):
        print("Retraining skipped: No logs found.")
        return False
        
    df = pd.read_csv(ACCUMULATED_LOGS_PATH)
    if len(df) < 10: 
        print(f"Retraining skipped: Not enough data ({len(df)} samples).")
        return False
        
    print(f"Triggering retraining on {len(df)} recent records...")
    X = df[['cpu_usage', 'memory_usage', 'temperature', 'latency', 'packet_loss']]
    
    new_detector = TelemetryAnomalyDetector()
    new_detector.train(X)
    
    global detector
    detector = new_detector
    joblib.dump(detector, MODEL_PATH)
    print("Retraining complete. New model is active.")
    return True

def flag_false_positive(timestamp: str):
    """
    Feedback Loop: User flags a past prediction as a False Positive.
    We duplicate this 'normal' data point 10 times to build a high-density 
    cluster, teaching the unsupervised model to ignore it next time.
    """
    if not os.path.exists(ACCUMULATED_LOGS_PATH):
        return False

    df = pd.read_csv(ACCUMULATED_LOGS_PATH)
    target_row = df[df['timestamp'] == timestamp]
    
    if target_row.empty:
        print(f"Error: Timestamp {timestamp} not found.")
        return False
        
    augmented_data = pd.concat([df] + [target_row] * 10, ignore_index=True)
    augmented_data.to_csv(ACCUMULATED_LOGS_PATH, index=False)
    
    print(f"SUCCESS: False positive logged for {timestamp}. Model memory adjusted.")
    return True