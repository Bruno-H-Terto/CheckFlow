from fastapi import FastAPI

from app.controllers.health_controller import router as health_router


def create_app() -> FastAPI:
    application = FastAPI(title="Checkflow API")
    application.include_router(health_router)
    return application


app = create_app()
