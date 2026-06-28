from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from adapters.postgres import PostgresPlanRepository, PostgresStepRepository
from app.controllers.health_controller import router as health_router
from app.controllers.plan_controller import router as plan_router
from app.controllers.step_controller import router as step_router
from app.ports.event_publisher import EventPublisher
from app.ports.plan_repository import PlanRepository
from app.ports.step_repository import StepRepository
from app.services import PlanService, StepExecutionScheduler, StepService
from config.settings import settings


def create_app(
    plan_repository: PlanRepository | None = None,
    event_publisher: EventPublisher | None = None,
    step_repository: StepRepository | None = None,
) -> FastAPI:
    plan_repo = plan_repository or PostgresPlanRepository.from_url(settings.DATABASE_URL)
    step_repo = step_repository or PostgresStepRepository.from_url(settings.DATABASE_URL)

    @asynccontextmanager
    async def lifespan(_application: FastAPI) -> AsyncGenerator[None]:
        try:
            yield
        finally:
            if isinstance(plan_repo, PostgresPlanRepository):
                plan_repo.close()
            if isinstance(step_repo, PostgresStepRepository):
                step_repo.close()

    application = FastAPI(title="Checkflow API", lifespan=lifespan)
    application.state.plan_service = PlanService(plan_repo)
    application.state.step_service = StepService(step_repo)
    application.state.step_execution_scheduler = (
        StepExecutionScheduler(event_publisher) if event_publisher is not None else None
    )
    application.include_router(health_router)
    application.include_router(plan_router)
    application.include_router(step_router)
    return application


app = create_app()
