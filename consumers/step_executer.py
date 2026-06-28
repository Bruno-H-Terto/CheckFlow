from datetime import UTC, datetime

from adapters.http import HttpxActionRunner
from adapters.kafka import KafkaEventPublisher
from adapters.postgres import PostgresStepRepository
from adapters.redis import RedisJsonCache
from config.settings import settings
from domain.entities.step import JsonValue
from domain.services import StepExecutor


def execute_step(step_id: int, execution_id: str) -> dict[str, JsonValue]:
    repository = PostgresStepRepository.from_url(settings.DATABASE_URL)
    cache = RedisJsonCache(settings.REDIS_URL, settings.CACHE_TTL_SECONDS)
    publisher = KafkaEventPublisher(settings.KAFKA_BOOTSTRAP_SERVERS)

    def notify(state: str, extra: dict[str, JsonValue] | None = None) -> None:
        payload: dict[str, JsonValue] = {
            "event_type": f"step.execution.{state}.v1",
            "execution_id": execution_id,
            "step_id": step_id,
            "occurred_at": datetime.now(UTC).isoformat(),
            **(extra or {}),
        }
        cache.set(f"execution:{execution_id}", payload)
        publisher.publish("checkflow.execution-events", execution_id, payload)

    try:
        notify("started")
        step = repository.get(step_id)
        if step is None:
            raise ValueError(f"Step {step_id} was not found")
        result = StepExecutor(HttpxActionRunner()).execute(step)
        completed: dict[str, JsonValue] = {
            "passed": result.passed,
            "status_code": result.action_result.status_code,
            "latency_ms": result.action_result.latency_ms,
            "assertions": [
                {
                    "target": item.assertion.target.value,
                    "actual": item.actual,
                    "passed": item.passed,
                }
                for item in result.assertions
            ],
        }
        notify("completed", completed)
        return completed
    except Exception as error:
        notify("failed", {"error": str(error)})
        raise
    finally:
        repository.close()
        cache.close()
        publisher.close()
