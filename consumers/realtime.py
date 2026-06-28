# pyright: reportUnknownMemberType=false

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from threading import Thread

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from adapters.kafka import KafkaEventConsumer, KafkaEventPublisher
from config.settings import settings
from domain.entities.step import JsonValue
from domain.events import ExecutionControl, PlanExecutionControlRequested


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[WebSocket, int] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    async def connect(self, websocket: WebSocket, plan_id: int) -> None:
        await websocket.accept()

        self._connections[websocket] = plan_id
        self._loop = asyncio.get_running_loop()

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.pop(websocket, None)

    async def broadcast(self, payload: dict[str, JsonValue]) -> None:
        plan_id = payload.get("plan_id")
        if not isinstance(plan_id, int):
            return
        for connection, subscribed_plan_id in tuple(self._connections.items()):
            if subscribed_plan_id == plan_id:
                await connection.send_json(payload)

    def broadcast_from_consumer(self, payload: dict[str, JsonValue]) -> None:
        if self._loop is not None:
            asyncio.run_coroutine_threadsafe(self.broadcast(payload), self._loop)


manager = ConnectionManager()
publisher = KafkaEventPublisher(settings.KAFKA_BOOTSTRAP_SERVERS)


def consume_events() -> None:
    KafkaEventConsumer(
        settings.KAFKA_BOOTSTRAP_SERVERS,
        "checkflow-realtime-websocket",
        ["checkflow.execution-events"],
    ).run(manager.broadcast_from_consumer)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    Thread(target=consume_events, daemon=True).start()

    yield

    publisher.close()


app = FastAPI(title="Checkflow Realtime", lifespan=lifespan)


@app.websocket("/ws/plans/{plan_id}/executions")
async def execution_events(websocket: WebSocket, plan_id: int) -> None:
    await manager.connect(websocket, plan_id)

    try:
        while True:
            message = await websocket.receive_json()
            command = ExecutionControl(message["command"])

            if command:
                event = PlanExecutionControlRequested(
                    execution_id=str(message["execution_id"]),
                    plan_id=plan_id,
                    command=command,
                )

                publisher.publish(
                    "checkflow.execution-events",
                    event.execution_id,
                    event.to_payload(),
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
