"""
conftest.py — pytest fixtures for SENTINEL-MPLS backend tests.
No test touches production metrics.db or accumulated_telemetry.csv.
"""

import os
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock


# ── Temp data dir with seeded CSVs ────────────────────────────────────────────

@pytest.fixture(scope="session")
def tmp_data(tmp_path_factory):
    d = tmp_path_factory.mktemp("data")

    # network_telemetry.csv
    pd.DataFrame({
        "cpu_usage":    [20, 30, 85, 90, 25, 70, 15, 95, 40, 60],
        "memory_usage": [30, 40, 80, 88, 35, 65, 20, 92, 50, 55],
        "temperature":  [35, 40, 70, 75, 38, 60, 30, 85, 45, 55],
        "latency":      [5,  8,  90, 120, 6, 50,  4, 150, 20, 40],
        "packet_loss":  [0,  0,  2,  5,   0,  1,  0,  8,  0,  1],
    }).to_csv(d / "network_telemetry.csv", index=False)

    # router_configs.csv
    pd.DataFrame({
        "node_id":     ["RTR-001", "RTR-002", "SW-001", "FW-001"],
        "device_type": ["router",  "router",  "switch", "firewall"],
        "config_text": [
            "interface GigabitEthernet0/0\n ip address 192.168.1.1 255.255.255.0\n no shutdown",
            "interface ge-0/0/0\n unit 0 { family inet { address 192.168.1.2/24; } }",
            "vlan 10\n name DATA\ninterface Ethernet1/1\n switchport access vlan 10",
            "set security zones security-zone trust interfaces ge-0/0/0",
        ],
    }).to_csv(d / "router_configs.csv", index=False)

    return d


@pytest.fixture(autouse=True)
def patch_paths(tmp_data, tmp_path, monkeypatch):
    """Redirect all file I/O away from production paths."""
    monkeypatch.setenv("SENTINEL_DATA_DIR",  str(tmp_data))
    monkeypatch.setenv("SENTINEL_MODEL_DIR", str(tmp_path / "models"))
    monkeypatch.setenv("SENTINEL_DB_PATH",   str(tmp_path / "metrics.db"))

    import config
    monkeypatch.setattr(config, "DATA_DIR",        str(tmp_data),              raising=False)
    monkeypatch.setattr(config, "MODEL_DIR",       str(tmp_path / "models"),   raising=False)
    monkeypatch.setattr(config, "METRICS_DB_PATH", str(tmp_path / "metrics.db"), raising=False)
    monkeypatch.setattr(config, "AUTH_DB_PATH",    str(tmp_path / "auth.db"),  raising=False)
    monkeypatch.setattr(config, "AUDIT_DB_PATH",   str(tmp_path / "audit.db"), raising=False)

    import ml_model
    monkeypatch.setattr(ml_model, "MODEL_PATH",
                        str(tmp_path / "models" / "isolation_forest.joblib"), raising=False)
    monkeypatch.setattr(ml_model, "ACCUMULATED_LOGS_PATH",
                        str(tmp_data / "accumulated_telemetry.csv"), raising=False)
    monkeypatch.setattr(ml_model, "FALSE_POSITIVE_LOG_PATH",
                        str(tmp_data / "false_positives.csv"), raising=False)


@pytest.fixture(scope="module")
def api_client(tmp_data):
    """FastAPI TestClient with heavy deps mocked out."""
    with patch("ml_model.train_model"), \
         patch("rag_system.init_rag"), \
         patch("telemetry_poller.engine.start"), \
         patch("auth.seed_default_users"):
        from fastapi.testclient import TestClient
        from main import app
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c