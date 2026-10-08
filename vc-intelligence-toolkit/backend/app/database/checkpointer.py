from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.core.config import settings

checkpointer: AsyncPostgresSaver | None = None
_checkpointer_cm = None


async def init_checkpointer() -> AsyncPostgresSaver:
    global checkpointer, _checkpointer_cm

    _checkpointer_cm = AsyncPostgresSaver.from_conn_string(
        settings.database_url
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