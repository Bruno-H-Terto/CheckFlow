from unittest.mock import AsyncMock

import pytest

from consumers.realtime import ConnectionManager


@pytest.mark.asyncio
async def test_broadcast_sends_only_to_connections_for_same_plan() -> None:
    manager = ConnectionManager()

    websocket_a = AsyncMock()
    websocket_b = AsyncMock()

    await manager.connect(websocket_a, plan_id=1)
    await manager.connect(websocket_b, plan_id=2)

    payload = {
        "event_type": "step.execution.started.v1",
        "plan_id": 1,
        "execution_id": "execution-123",
    }

    await manager.broadcast(payload)

    websocket_a.send_json.assert_called_once_with(payload)
    websocket_b.send_json.assert_not_called()


@pytest.mark.asyncio
async def test_broadcast_ignores_payload_without_plan_id() -> None:
    manager = ConnectionManager()

    websocket = AsyncMock()

    await manager.connect(websocket, plan_id=1)

    await manager.broadcast(
        {
            "event_type": "step.execution.started.v1",
            "execution_id": "execution-123",
        }
    )

    websocket.send_json.assert_not_called()


@pytest.mark.asyncio
async def test_disconnect_removes_connection() -> None:
    manager = ConnectionManager()

    websocket = AsyncMock()

    await manager.connect(websocket, plan_id=1)
    manager.disconnect(websocket)

    await manager.broadcast(
        {
            "event_type": "step.execution.started.v1",
            "plan_id": 1,
            "execution_id": "execution-123",
        }
    )

    websocket.send_json.assert_not_called()