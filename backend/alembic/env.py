from alembic import context
from app.db import get_engine
from app.models import Base

if context.is_offline_mode():
    raise RuntimeError("Use online migration mode with DATABASE_URL configured")

with get_engine().connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
