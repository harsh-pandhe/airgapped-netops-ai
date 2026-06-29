"""
scenarios.py — Demo scenario injection for SENTINEL-MPLS.
Injects controlled anomalies into MockTelemetrySource for judge demos.
"""

from typing import Literal

SCENARIOS: dict[str, dict] = {
    "ddos": {
        "description": "DDoS attack on RTR-002: packet loss spike + latency surge",
        "overrides": {
            "RTR-002": {"cpu": 98.0, "memory": 95.0, "latency": 850.0,
                        "packet_loss": 22.0, "temperature": 88.0}
        },
        "duration_ticks": 15,
    },
    "link_flap": {
        "description": "SW-001 link flap: intermittent packet loss",
        "overrides": {
            "SW-001": {"packet_loss": 18.0, "latency": 200.0}
        },
        "duration_ticks": 10,
    },
    "thermal_throttle": {
        "description": "FW-001 thermal throttle: high temp causes CPU throttle",
        "overrides": {
            "FW-001": {"temperature": 94.0, "cpu": 88.0, "latency": 120.0}
        },
        "duration_ticks": 20,
    },
    "cascade": {
        "description": "Cascade failure: RTR-001 down causes RTR-002 overload",
        "overrides": {
            "RTR-001": {"cpu": 99.0, "latency": 1200.0, "packet_loss": 30.0},
            "RTR-002": {"cpu": 92.0, "latency": 400.0,  "packet_loss": 8.0},
        },
        "duration_ticks": 25,
    },
}

ScenarioName = Literal["ddos", "link_flap", "thermal_throttle", "cascade"]


def inject_scenario(scenario_name: str, poller) -> dict:
    """
    Apply scenario overrides to the active MockTelemetrySource.
    Returns scenario info dict.
    """
    if scenario_name not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario_name}")

    s = SCENARIOS[scenario_name]
    ticks = s["duration_ticks"]

    for node_id, overrides in s["overrides"].items():
        poller.inject_override(node_id, overrides, ticks)

    duration_seconds = ticks * 2   # 2s per tick (WebSocket interval)
    return {
        "scenario":         scenario_name,
        "description":      s["description"],
        "duration_seconds": duration_seconds,
        "duration_ticks":   ticks,
        "nodes_affected":   list(s["overrides"].keys()),
    }


def reset_scenarios(poller):
    """Clear all active overrides."""
    poller.clear_overrides()
    return {"status": "reset", "message": "All overrides cleared"}


def get_scenario_list() -> list[dict]:
    return [
        {
            "name":             name,
            "description":      s["description"],
            "duration_seconds": s["duration_ticks"] * 2,
            "nodes_affected":   list(s["overrides"].keys()),
        }
        for name, s in SCENARIOS.items()
    ]