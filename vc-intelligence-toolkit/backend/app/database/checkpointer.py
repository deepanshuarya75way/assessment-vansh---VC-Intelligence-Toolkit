from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.core.config import settings

checkpointer: AsyncPostgresSaver | None = None
_checkpointer_cm = None


def _get_checkpointer_database_url() -> str:
    database_url = settings.database_url

    if database_url.startswith("postgresql+asyncpg://"):
        return database_url.replace(
            "postgresql+asyncpg://",
            "postgresql://",
            1,
        )

    if database_url.startswith("postgres+asyncpg://"):
        return database_url.replace(
            "postgres+asyncpg://",
            "postgresql://",
            1,
        )

    return database_url


async def init_checkpointer() -> AsyncPostgresSaver:
    global checkpointer, _checkpointer_cm

    database_url = _get_checkpointer_database_url()

    _checkpointer_cm = AsyncPostgresSaver.from_conn_string(
        database_url
    )

    checkpointer = await _checkpointer_cm.__aenter__()

    await checkpointer.setup()

    return checkpointer


async def close_checkpointer() -> None:
    global checkpointer, _checkpointer_cm

    if _checkpointer_cm is not None:
        await _checkpointer_cm.__aexit__(None, None, None)

    checkpointer = None
    _checkpointer_cm = None