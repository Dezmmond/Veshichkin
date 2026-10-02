from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from veshichkin.core.config import get_settings

engine = create_engine(
    str(get_settings().database_url),
    connect_args={"connect_timeout": 3},
    pool_timeout=3,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine)


def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
