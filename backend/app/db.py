import os
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session


@lru_cache
def get_engine():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is required. Start the API with --env-file ../.env")
    return create_engine(url, pool_pre_ping=True)


def get_session():
    with Session(get_engine()) as session:
        yield session
