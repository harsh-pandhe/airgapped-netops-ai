"""
telemetry_ws.py — WebSocket broadcast manager for live telemetry stream.
Track 13: ConnectionManager pattern, shared engine singleton.
"""

from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect
import asyncio
from telemetry_poller import engine
import ml_model


class ConnectionManager:
    def __init__(self):
        self._active: set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._active.add(ws)

    def disconnect(self, ws: WebSocket):
        self._active.discard(ws)

    async def broadcast(self, data: dict):
        dead = set()
        for ws in self._active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.add(ws)
        self._active -= dead


ws_manager = ConnectionManager()


async def telemetry_broadcast_loop(websocket: WebSocket):
    """
    Runs per connected client.
    Ticks engine, runs predict_node per node, broadcasts full payload.
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            state = engine.get_state()
            payload = {}
            for node_id, vals in state.items():
                pred = ml_model.predict_node(
                    vals["cpu"], vals["memory"], vals["temperature"],
                    vals["latency"], vals["packet_loss"],
                    node_id=node_id,
                )
                payload[node_id] = {
                    **vals,
                    "anomaly":        pred["anomaly"],
                    "anomaly_score":  pred["anomaly_score"],
                    "explanation":    pred["explanation"],
                    "feature_impacts": pred["feature_impacts"],
                    "timestamp":      pred["timestamp"],
                }
            await websocket.send_json(payload)
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)