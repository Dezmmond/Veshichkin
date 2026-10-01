from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from veshichkin.catalog.router import router as catalog_router
from veshichkin.categories.router import router as categories_router
from veshichkin.core.config import Settings, get_settings
from veshichkin.core.errors import ApplicationError, application_error_handler
from veshichkin.core.static import SPAStaticFiles
from veshichkin.db.session import engine
from veshichkin.health.router import router
from veshichkin.profile.router import router as profile_router
from veshichkin.reference_data.router import router as reference_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    try:
        yield
    finally:
        engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    application = FastAPI(title=settings.application_name, debug=settings.debug, lifespan=lifespan)
    application.add_exception_handler(ApplicationError, application_error_handler)
    application.include_router(router, prefix="/api")
    application.include_router(categories_router, prefix="/api")
    application.include_router(reference_router, prefix="/api")
    application.include_router(catalog_router, prefix="/api")
    application.include_router(profile_router, prefix="/api")
    if settings.static_dir is not None:
        application.mount("/", SPAStaticFiles(directory=settings.static_dir, html=True))
    return application


app = create_app()
