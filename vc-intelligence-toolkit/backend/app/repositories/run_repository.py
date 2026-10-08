from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.run import Run


async def create(
    db: AsyncSession,
    module_name: str,
    status: str,
    candidate_id: int | None = None,
    thread_id: str | None = None,
) -> Run:
    run = Run(
        module_name=module_name,
        status=status,
        candidate_id=candidate_id,
        thread_id=thread_id,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


async def update_thread_id(
    db: AsyncSession,
    run_id: int,
    thread_id: str,
) -> Run | None:
    run = await db.get(Run, run_id)

    if run is None:
        return None

    run.thread_id = thread_id

    await db.commit()
    await db.refresh(run)

    return run


async def list_all(
    db: AsyncSession,
    limit: int = 50,
) -> list[Run]:
    result = await db.execute(
        select(Run)
        .order_by(Run.started_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_by_id(
    db: AsyncSession,
    run_id: int,
) -> Run | None:
    return await db.get(Run, run_id)


async def update_status(
    db: AsyncSession,
    run_id: int,
    status: str,
    completed_at: datetime | None = None,
) -> Run | None:
    run = await db.get(Run, run_id)

    if run is None:
        return None

    run.status = status

    if status == "completed":
        run.failed_node = None
        run.error = None

    if completed_at is not None:
        run.completed_at = completed_at
        
    await db.commit()
    await db.refresh(run)

    return run


async def update_failure(
    db: AsyncSession,
    run_id: int,
    failed_node: str,
    error: str,
) -> Run | None:
    run = await db.get(Run, run_id)

    if run is None:
        return None

    run.status = "failed"
    run.failed_node = failed_node
    run.error = error
    run.completed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(run)

    return run