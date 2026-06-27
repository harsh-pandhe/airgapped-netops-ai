import time
from functools import wraps

# Global metrics storage
metrics = {
    "inference_times": [],
    "retrieval_durations": [],
    "total_tokens_generated": 0
}

def track_performance(metric_type):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            duration = (time.perf_counter() - start_time) * 1000  # ms
            
            if metric_type == "inference":
                metrics["inference_times"].append(duration)
            elif metric_type == "retrieval":
                metrics["retrieval_durations"].append(duration)
                
            return result
        return wrapper
    return decorator