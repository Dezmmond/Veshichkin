from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from veshichkin.core.config import Settings, get_settings
from veshichkin.core.errors import ApplicationError, application_error_handler
from veshichkin.core.static import SPAStaticFiles
from veshichkin.db.session import engine
from veshichkin.health.router import router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    try:
        yield
    finally:
        engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    application = FastAPI(
        title=settings.application_name, debug=settings.debug, lifespan=lifespan
    )
    application.add_exception_handler(ApplicationError, application_error_handler)
    application.include_router(router, prefix="/api")
    if settings.static_dir is not None:
        application.mount("/", SPAStaticFiles(directory=settings.static_dir, html=True))
    return application


app = create_app()
