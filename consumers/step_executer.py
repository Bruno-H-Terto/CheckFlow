from datetime import UTC, datetime
from typing import cast

from adapters.http import HttpxActionRunner
from adapters.kafka import KafkaEventPublisher
from adapters.postgres import PostgresExecutionRepository, PostgresStepRepository
from adapters.redis import RedisJsonCache
from config.settings import settings
from domain.entities.step import JsonValue
from domain.services import StepExecutor
from domain.services import extract_variables, render_step
from domain.entities.execution import ExecutionStatus


def execute_step(
    plan_id: int,
    step_id: int,
    execution_id: str,
) -> dict[str, JsonValue]:
    repository = PostgresStepRepository.from_url(settings.DATABASE_URL)
    executions = PostgresExecutionRepository.from_url(settings.DATABASE_URL)
    cache = RedisJsonCache(settings.REDIS_URL, settings.CACHE_TTL_SECONDS)
    publisher = KafkaEventPublisher(settings.KAFKA_BOOTSTRAP_SERVERS)

    def notify(state: str, extra: dict[str, JsonValue] | None = None) -> None:
        payload: dict[str, JsonValue] = {
            "event_type": f"step.execution.{state}.v1",
            "execution_id": execution_id,
            "plan_id": plan_id,
            "step_id": step_id,
            "occurred_at": datetime.now(UTC).isoformat(),
            **(extra or {}),
        }
        cache.set(f"plan-execution:{execution_id}", payload)
        publisher.publish("checkflow.execution-events", execution_id, payload)

    try:
        notify("started")
        executions.start_step(execution_id, step_id)
        step = repository.get(plan_id, step_id)
        if step is None:
            raise ValueError(f"Step {step_id} was not found")
        execution = executions.get(execution_id)
        if execution is None:
            raise ValueError(f"Execution {execution_id} was not found")
        result = StepExecutor(HttpxActionRunner()).execute(render_step(step, execution.variables))
        assertion_payloads: list[dict[str, JsonValue]] = [
            {"target": item.assertion.target.value, "actual": item.actual, "passed": item.passed}
            for item in result.assertions
        ]
        completed: dict[str, JsonValue] = {
            "passed": result.passed,
            "status_code": result.action_result.status_code,
            "latency_ms": result.action_result.latency_ms,
            "assertions": cast(JsonValue, assertion_payloads),
        }
        if result.passed:
            extracted = extract_variables(step.extracts, result.action_result)
            if extracted:
                executions.merge_variables(execution_id, extracted)
            executions.finish_step(execution_id, step_id, ExecutionStatus.COMPLETED, status_code=result.action_result.status_code, latency_ms=result.action_result.latency_ms, assertions=assertion_payloads)
            notify("completed", completed)
        else:
            executions.finish_step(execution_id, step_id, ExecutionStatus.FAILED, status_code=result.action_result.status_code, latency_ms=result.action_result.latency_ms, assertions=assertion_payloads, error="Step assertions failed")
            notify("failed", {**completed, "error": "Step assertions failed"})
        return completed
    except Exception as error:
        try:
            executions.finish_step(execution_id, step_id, ExecutionStatus.FAILED, error=str(error))
        except ValueError:
            pass
        notify("failed", {"error": str(error)})
        raise
    finally:
        repository.close()
        executions.close()
        cache.close()
        publisher.close()
