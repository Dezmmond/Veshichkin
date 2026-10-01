from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from veshichkin.core.config import get_settings
from veshichkin.core.errors import ApplicationError, application_error_handler
from veshichkin.db.session import engine
from veshichkin.health.router import router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    try:
        yield
    finally:
        engine.dispose()


settings = get_settings()
app = FastAPI(title=settings.application_name, debug=settings.debug, lifespan=lifespan)
app.add_exception_handler(ApplicationError, application_error_handler)
app.include_router(router, prefix="/api")
