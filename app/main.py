from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from adapters.postgres import PostgresExecutionRepository, PostgresPlanRepository, PostgresStepRepository
from adapters.kafka import KafkaEventPublisher
from app.controllers.health_controller import router as health_router
from app.controllers.plan_controller import router as plan_router
from app.controllers.step_controller import router as step_router
from app.ports.event_publisher import EventPublisher
from app.ports.plan_repository import PlanRepository
from app.ports.step_repository import StepRepository
from app.ports.execution_repository import ExecutionRepository
from app.services import PlanExecutionScheduler, PlanService, StepService
from config.settings import settings

OPENAPI_TAGS = [
    {"name": "health", "description": "Disponibilidade da API."},
    {"name": "plans", "description": "Definição dos planos de validação."},
    {"name": "steps", "description": "Blocos executáveis e seus agendamentos."},
]


def create_app(
    plan_repository: PlanRepository | None = None,
    event_publisher: EventPublisher | None = None,
    step_repository: StepRepository | None = None,
    execution_repository: ExecutionRepository | None = None,
) -> FastAPI:
    plan_repo = plan_repository or PostgresPlanRepository.from_url(
        settings.DATABASE_URL
    )
    step_repo = step_repository or PostgresStepRepository.from_url(
        settings.DATABASE_URL
    )
    execution_repo = execution_repository
    if execution_repo is None and plan_repository is None:
        execution_repo = PostgresExecutionRepository.from_url(settings.DATABASE_URL)

    @asynccontextmanager
    async def lifespan(_application: FastAPI) -> AsyncGenerator[None]:
        try:
            yield
        finally:
            if isinstance(plan_repo, PostgresPlanRepository):
                plan_repo.close()
            if isinstance(step_repo, PostgresStepRepository):
                step_repo.close()
            if isinstance(execution_repo, PostgresExecutionRepository):
                execution_repo.close()
            if isinstance(event_publisher, KafkaEventPublisher):
                event_publisher.close()

    application = FastAPI(
        title="Checkflow API",
        summary="Validador de fluxos para sistemas distribuídos",
        description=(
            "Crie planos e steps, dispare execuções em background e acompanhe "
            "os eventos pelo serviço realtime."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
    )
    application.state.plan_service = PlanService(plan_repo)
    application.state.step_service = StepService(step_repo)
    application.state.execution_repository = execution_repo
    application.state.plan_execution_scheduler = (
        PlanExecutionScheduler(event_publisher, execution_repo) if event_publisher is not None else None
    )
    application.include_router(health_router)
    application.include_router(plan_router)
    application.include_router(step_router)

    return application


app = create_app(event_publisher=KafkaEventPublisher(settings.KAFKA_BOOTSTRAP_SERVERS))
