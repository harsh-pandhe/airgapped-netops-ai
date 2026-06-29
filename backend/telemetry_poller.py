"""
telemetry_poller.py — Pluggable telemetry source for SENTINEL-MPLS.

Classes:
  TelemetrySource       — abstract base
  MockTelemetrySource   — random walk + correlated spikes (demo/dev)
  SNMPTelemetrySource   — real SNMP via pysnmp (stub, falls back to mock)

The module-level `engine` singleton is the MockTelemetryEngine used by
Track 13 WebSocket. `get_poller()` returns the active source per config.
"""

import random
import threading
import time
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from config import TELEMETRY_MODE, TELEMETRY_INTERVAL_S, SNMP_COMMUNITY, SNMP_TARGETS

# ── Types ─────────────────────────────────────────────────────────────────────

@dataclass
class NodeState:
    node_id:     str
    label:       str
    ip:          str
    cpu:         float
    memory:      float
    temperature: float
    latency:     float
    packet_loss: float
    # walk deltas
    _cpu_d:  float = field(default=0.0, repr=False)
    _mem_d:  float = field(default=0.0, repr=False)
    _temp_d: float = field(default=0.0, repr=False)
    _lat_d:  float = field(default=0.0, repr=False)
    _loss_d: float = field(default=0.0, repr=False)

    def as_dict(self) -> dict:
        return {
            "cpu":         round(self.cpu, 1),
            "memory":      round(self.memory, 1),
            "temperature": round(self.temperature, 1),
            "latency":     round(self.latency, 2),
            "packet_loss": round(self.packet_loss, 3),
        }

    def as_tuple(self) -> tuple:
        return (self.cpu, self.memory, self.temperature, self.latency, self.packet_loss)


# ── Abstract base ─────────────────────────────────────────────────────────────

class TelemetrySource(ABC):
    @abstractmethod
    def get_state(self) -> dict[str, dict]:
        """Returns {node_id: {cpu, memory, temperature, latency, packet_loss}}"""
        ...

    def get_tuple(self, node_id: str) -> tuple | None:
        state = self.get_state()
        v = state.get(node_id)
        if not v:
            return None
        return (v["cpu"], v["memory"], v["temperature"], v["latency"], v["packet_loss"])

    def snmp_get(self, node_id: str) -> dict:
        """SNMP OID stub — override in SNMPTelemetrySource."""
        state = self.get_state().get(node_id, {})
        return {
            "1.3.6.1.4.1.9.9.109.1.1.1.1.8.1": state.get("cpu"),
            "1.3.6.1.2.1.25.2.3.1.6.1":         state.get("memory"),
            "1.3.6.1.4.1.9.9.13.1.3.1.3.1":     state.get("temperature"),
            "1.3.6.1.2.1.31.1.1.1.10.1":        state.get("latency"),
            "1.3.6.1.2.1.2.2.1.13.1":           state.get("packet_loss"),
        }


# ── Initial node definitions ──────────────────────────────────────────────────

_INITIAL_NODES = [
    {"node_id": "RTR-001", "label": "Cisco ASR",      "ip": "192.168.1.1",
     "cpu": 45.0, "memory": 60.0, "temperature": 55.0, "latency": 20.0,  "packet_loss": 0.1},
    {"node_id": "RTR-002", "label": "Juniper MX",     "ip": "192.168.1.2",
     "cpu": 75.0, "memory": 72.0, "temperature": 68.0, "latency": 80.0,  "packet_loss": 0.5},
    {"node_id": "SW-001",  "label": "Cisco Nexus",    "ip": "192.168.2.1",
     "cpu": 20.0, "memory": 30.0, "temperature": 40.0, "latency": 5.0,   "packet_loss": 0.0},
    {"node_id": "FW-001",  "label": "Palo Alto NGFW", "ip": "192.168.0.1",
     "cpu": 55.0, "memory": 50.0, "temperature": 52.0, "latency": 30.0,  "packet_loss": 0.2},
]

# Base values per node for latency correlation
_BASE_CPU: dict[str, float] = {d["node_id"]: d["cpu"] for d in _INITIAL_NODES}
_BASE_LAT: dict[str, float] = {d["node_id"]: d["latency"] for d in _INITIAL_NODES}


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


# ── MockTelemetrySource ───────────────────────────────────────────────────────

class MockTelemetrySource(TelemetrySource):
    """
    Random walk telemetry with:
    - Gaussian walk per metric
    - Correlated CPU→latency: latency = base * (1 + 0.04 * max(0, cpu - 60))
    - Anomaly injection: every ~45 ticks, spike one node for 8-12 ticks
    - RTR-002 has higher baseline (matches training data)
    """

    SPIKE_PROB   = 1 / 45     # ~once per 45 ticks
    SPIKE_CPU    = (85, 99)
    SPIKE_TICKS  = (8, 12)

    def __init__(self, interval: float = TELEMETRY_INTERVAL_S):
        self._interval = interval
        self._lock     = threading.RLock()
        self._nodes: dict[str, NodeState] = {
            d["node_id"]: NodeState(**d) for d in _INITIAL_NODES
        }
        self._spike_countdown: dict[str, int]   = {n: 0 for n in self._nodes}
        self._spike_cpu_target: dict[str, float] = {n: 0 for n in self._nodes}
        self._overrides: dict[str, dict]         = {}   # scenario overrides
        self._override_countdown: dict[str, int] = {}
        self._tick_count = 0
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def _walk(self, val: float, delta: float, step: float,
               lo: float, hi: float) -> tuple[float, float]:
        delta = _clamp(delta + random.gauss(0, step * 0.3), -step * 2, step * 2)
        return _clamp(val + delta, lo, hi), delta

    def _tick(self):
        with self._lock:
            self._tick_count += 1

            for nid, ns in self._nodes.items():
                # ── Scenario override ─────────────────────────────────────
                if nid in self._overrides and self._override_countdown.get(nid, 0) > 0:
                    ov = self._overrides[nid]
                    ns.cpu         = ov.get("cpu",         ns.cpu)
                    ns.memory      = ov.get("memory",      ns.memory)
                    ns.temperature = ov.get("temperature", ns.temperature)
                    ns.latency     = ov.get("latency",     ns.latency)
                    ns.packet_loss = ov.get("packet_loss", ns.packet_loss)
                    self._override_countdown[nid] -= 1
                    if self._override_countdown[nid] <= 0:
                        self._overrides.pop(nid, None)
                    continue

                # ── Anomaly spike ──────────────────────────────────────────
                if self._spike_countdown[nid] > 0:
                    target = self._spike_cpu_target[nid]
                    ns.cpu = _clamp(ns.cpu + (target - ns.cpu) * 0.3, 0, 100)
                    ns.packet_loss = _clamp(ns.packet_loss + random.uniform(0.5, 2.0), 0, 30)
                    self._spike_countdown[nid] -= 1
                elif random.random() < self.SPIKE_PROB:
                    self._spike_countdown[nid]  = random.randint(*self.SPIKE_TICKS)
                    self._spike_cpu_target[nid] = random.uniform(*self.SPIKE_CPU)

                # ── Random walk ───────────────────────────────────────────
                ns.cpu,         ns._cpu_d  = self._walk(ns.cpu,         ns._cpu_d,  1.5, 5,   100)
                ns.memory,      ns._mem_d  = self._walk(ns.memory,      ns._mem_d,  1.0, 10,  100)
                ns.temperature, ns._temp_d = self._walk(ns.temperature, ns._temp_d, 0.5, 20,  95)
                ns.packet_loss, ns._loss_d = self._walk(ns.packet_loss, ns._loss_d, 0.1, 0,   30)

                # ── Latency correlated with CPU ───────────────────────────
                base_lat = _BASE_LAT[nid]
                base_cpu = _BASE_CPU[nid]
                ns.latency = _clamp(
                    base_lat * (1 + 0.04 * max(0, ns.cpu - base_cpu))
                    + random.gauss(0, 3),
                    1, 1000
                )

    def _run(self):
        while True:
            self._tick()
            time.sleep(self._interval)

    # ── Public API ────────────────────────────────────────────────────────────

    def get_state(self) -> dict[str, dict]:
        with self._lock:
            return {nid: ns.as_dict() for nid, ns in self._nodes.items()}

    def get_node_state(self, node_id: str) -> NodeState | None:
        with self._lock:
            return self._nodes.get(node_id)

    def inject_override(self, node_id: str, overrides: dict, duration_ticks: int):
        with self._lock:
            self._overrides[node_id]          = overrides
            self._override_countdown[node_id] = duration_ticks

    def clear_overrides(self):
        with self._lock:
            self._overrides.clear()
            self._override_countdown.clear()

    def get_override_remaining(self, node_id: str) -> int:
        with self._lock:
            return self._override_countdown.get(node_id, 0)


# ── SNMPTelemetrySource (stub) ────────────────────────────────────────────────

class SNMPTelemetrySource(TelemetrySource):
    """
    Reads real SNMP OIDs via pysnmp.
    Falls back to MockTelemetrySource if unreachable.
    Swap _mock for None and implement _poll_snmp() for production.
    """

    # Real OID map (Cisco-centric, adaptable)
    OID_MAP = {
        "cpu":         "1.3.6.1.4.1.9.9.109.1.1.1.1.8.1",
        "memory":      "1.3.6.1.2.1.25.2.3.1.6.1",
        "temperature": "1.3.6.1.4.1.9.9.13.1.3.1.3.1",
        "latency":     "1.3.6.1.2.1.31.1.1.1.10.1",
        "packet_loss": "1.3.6.1.2.1.2.2.1.13.1",
    }

    def __init__(self):
        self._mock = MockTelemetrySource()
        self._mock.start()
        self._targets  = [t for t in SNMP_TARGETS if t.strip()]
        self._community = SNMP_COMMUNITY

    def _poll_snmp(self, target_ip: str) -> dict | None:
        """
        Real pysnmp GET — returns {metric: value} or None on failure.
        Replace the body with actual pysnmp calls when hardware available.
        """
        try:
            from pysnmp.hlapi import (
                getCmd, SnmpEngine, CommunityData,
                UdpTransportTarget, ContextData, ObjectType, ObjectIdentity
            )
            results = {}
            for metric, oid in self.OID_MAP.items():
                for (errorIndication, errorStatus, _, varBinds) in getCmd(
                    SnmpEngine(),
                    CommunityData(self._community),
                    UdpTransportTarget((target_ip, 161), timeout=2, retries=1),
                    ContextData(),
                    ObjectType(ObjectIdentity(oid))
                ):
                    if errorIndication or errorStatus:
                        return None
                    for varBind in varBinds:
                        results[metric] = float(varBind[1])
            return results
        except Exception:
            return None

    def get_state(self) -> dict[str, dict]:
        if not self._targets:
            return self._mock.get_state()
        # Try real SNMP; fall back to mock on failure
        state = {}
        node_ids = list(self._mock.get_state().keys())
        for i, (node_id, target_ip) in enumerate(zip(node_ids, self._targets)):
            data = self._poll_snmp(target_ip)
            if data:
                state[node_id] = {k: round(float(v), 2) for k, v in data.items()}
            else:
                state[node_id] = self._mock.get_state().get(node_id, {})
        return state


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_poller() -> TelemetrySource:
    if TELEMETRY_MODE == "snmp":
        return SNMPTelemetrySource()
    return MockTelemetrySource()


# Module-level singleton used by WebSocket engine (Track 13)
engine: MockTelemetrySource = MockTelemetrySource()