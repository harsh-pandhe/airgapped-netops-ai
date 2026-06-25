import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import os
import warnings

# Suppress warnings for valid feature names
warnings.filterwarnings("ignore", category=UserWarning)

MODEL = None

def train_model():
    global MODEL
    data_path = os.path.join(os.path.dirname(__file__), '../data/network_telemetry.csv')
    df = pd.read_csv(data_path)
    
    # Simple feature set
    X = df[['cpu_usage', 'memory_usage', 'temperature', 'latency', 'packet_loss']]
    y = df['status']
    
    MODEL = RandomForestClassifier(n_estimators=10, random_state=42)
    MODEL.fit(X.values, y.values)  # Using .values to avoid feature name warnings during prediction
    print("ML Predictor trained successfully.")

def predict_node(cpu: float, memory: float, temp: float, latency: float, loss: float):
    if MODEL is None:
        train_model()
    prediction = MODEL.predict([[cpu, memory, temp, latency, loss]])
    return prediction[0]
