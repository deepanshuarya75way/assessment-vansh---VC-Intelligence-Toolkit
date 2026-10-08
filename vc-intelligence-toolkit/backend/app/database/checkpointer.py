from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection

from app.core.config import settings


checkpointer: AsyncPostgresSaver | None = None
_checkpointer_conn: AsyncConnection | None = None


def _get_checkpointer_database_url() -> str:
    database_url = settings.database_url

    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace(
            "postgresql+asyncpg://",
            "postgresql://",
            1,
        )

    if database_url.startswith("postgres+asyncpg://"):
        database_url = database_url.replace(
            "postgres+asyncpg://",
            "postgresql://",
            1,
        )

    return database_url


async def init_checkpointer() -> AsyncPostgresSaver:
    global checkpointer, _checkpointer_conn

    database_url = _get_checkpointer_database_url()

    _checkpointer_conn = await AsyncConnection.connect(
        database_url,
        prepare_threshold=None,
    )

    checkpointer = AsyncPostgresSaver(_checkpointer_conn)

    await checkpointer.setup()

    return checkpointer


async def close_checkpointer() -> None:
    global checkpointer, _checkpointer_conn

    if _checkpointer_conn is not None:
        await _checkpointer_conn.close()

    checkpointer = None
    _checkpointer_conn = None