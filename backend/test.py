import json
from ml_model import train_model, predict_node

print("--- Testing Normal Traffic ---")
normal_result = predict_node(45.0, 60.0, 55.0, 20.0, 0.1)
print(json.dumps(normal_result, indent=2))

print("\n--- Testing Spiked Traffic (DDoS / Outage simulation) ---")
spiked_result = predict_node(99.5, 95.0, 88.0, 850.0, 25.0)
print(json.dumps(spiked_result, indent=2))