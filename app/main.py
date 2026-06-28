from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from adapters.postgres import PostgresPlanRepository
from app.controllers.health_controller import router as health_router
from app.controllers.plan_controller import router as plan_router
from app.ports.plan_repository import PlanRepository
from app.services import PlanService
from config.settings import settings


def create_app(plan_repository: PlanRepository | None = None) -> FastAPI:
    repository = plan_repository or PostgresPlanRepository.from_url(settings.DATABASE_URL)

    @asynccontextmanager
    async def lifespan(_application: FastAPI) -> AsyncGenerator[None]:
        try:
            yield
        finally:
            if isinstance(repository, PostgresPlanRepository):
                repository.close()

    application = FastAPI(title="Checkflow API", lifespan=lifespan)
    application.state.plan_service = PlanService(repository)
    application.include_router(health_router)
    application.include_router(plan_router)
    return application


app = create_app()
