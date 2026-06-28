# pyright: reportUnknownMemberType=false

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from threading import Thread

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from adapters.kafka import KafkaEventConsumer, KafkaEventPublisher
from config.settings import settings
from domain.entities.step import JsonValue
from domain.events import ExecutionControl, StepExecutionControlRequested


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)
        self._loop = asyncio.get_running_loop()

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, payload: dict[str, JsonValue]) -> None:
        for connection in tuple(self._connections):
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


@app.websocket("/ws/executions")
async def execution_events(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        while True:
            message = await websocket.receive_json()
            command = ExecutionControl(message["command"])
            event = StepExecutionControlRequested(
                execution_id=str(message["execution_id"]),
                step_id=int(message["step_id"]),
                command=command,
            )
            publisher.publish(
                "checkflow.execution-events",
                event.execution_id,
                event.to_payload(),
            )
    except WebSocketDisconnect:
        manager.disconnect(websocket)
