import psutil
import pynvml

# Initialize NVML for GPU monitoring
try:
    pynvml.nvmlInit()
except Exception as e:
    print(f"GPU monitoring unavailable: {e}")

def get_system_metrics():
    # CPU Usage (%)
    cpu_usage = psutil.cpu_percent(interval=None) # interval=None for non-blocking
    
    # RAM Usage
    memory = psutil.virtual_memory()
    ram_usage = memory.percent
    
    # GPU Usage (if available)
    gpu_usage = 0
    gpu_memory = 0
    try:
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        gpu_info = pynvml.nvmlDeviceGetUtilizationRates(handle)
        mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        gpu_usage = gpu_info.gpu
        gpu_memory = (mem_info.used / mem_info.total) * 100
    except:
        pass # GPU monitoring skipped if no NVIDIA card
        
    return {
        "cpu_percent": cpu_usage,
        "ram_percent": ram_usage,
        "gpu_percent": gpu_usage,
        "gpu_mem_percent": round(gpu_memory, 2)
    }