from datetime import datetime

from app.database import checkpointer as checkpointer_module
from app.database.session import get_sessionmaker
from app.graphs.moatlens.graph import (
    MoatlensNodeError,
    build_moatlens_graph,
)
from app.models.report import ReportType
from app.repositories import (
    candidate_repository,
    report_repository,
    run_repository,
)
from app.schemas.candidate import CandidateOut
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def run_moatlens_evaluation(candidate_id: int) -> dict:
    """
    Start a completely fresh MoatLens evaluation.
    """

    logger.info(
        "Starting MoatLens evaluation for candidate %s",
        candidate_id,
    )

    sessionmaker = get_sessionmaker()

    async with sessionmaker() as session:
        candidate = await candidate_repository.get_by_id(
            session,
            candidate_id,
        )

        if candidate is None:
            raise ValueError(
                f"Candidate {candidate_id} not found."
            )

        candidate_payload = (
            CandidateOut.model_validate(candidate).model_dump()
        )

        run = await run_repository.create(
            session,
            module_name="moatlens",
            status="running",
            candidate_id=candidate_id,
        )

    if checkpointer_module.checkpointer is None:
        raise RuntimeError(
            "LangGraph checkpointer is not initialized."
        )

    moatlens_graph = build_moatlens_graph(
        checkpointer_module.checkpointer
    )

    thread_id = f"moatlens-run-{run.id}"

    async with sessionmaker() as session:
        await run_repository.update_thread_id(
            session,
            run_id=run.id,
            thread_id=thread_id,
        )

    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    try:
        state = await moatlens_graph.ainvoke(
            {
                "candidate": candidate_payload,
                "retry_count": 0,
            },
            config=config,
        )

        final_report = state["final_report"]

        async with sessionmaker() as session:
            await report_repository.create(
                session,
                candidate_id=candidate_id,
                run_id=run.id,
                report_type=ReportType.diligence,
                content=final_report,
            )

            await run_repository.update_status(
                session,
                run_id=run.id,
                status="completed",
                completed_at=datetime.utcnow(),
            )

        logger.info(
            "MoatLens evaluation completed for candidate %s",
            candidate_id,
        )

        return final_report

    except MoatlensNodeError as exc:
        async with sessionmaker() as session:
            await run_repository.update_failure(
                session,
                run_id=run.id,
                failed_node=exc.node_name,
                error=str(exc.original_error),
            )

        logger.exception(
            "MoatLens evaluation failed at node %s",
            exc.node_name,
        )

        raise

    except Exception as exc:
        async with sessionmaker() as session:
            await run_repository.update_failure(
                session,
                run_id=run.id,
                failed_node="unknown",
                error=str(exc),
            )

        logger.exception(
            "MoatLens evaluation failed",
        )

        raise


async def retry_moatlens_evaluation(run_id: int) -> dict:
    """
    Resume a failed MoatLens evaluation from its
    last LangGraph checkpoint.
    """

    logger.info(
        "Retrying MoatLens run %s",
        run_id,
    )

    sessionmaker = get_sessionmaker()

    async with sessionmaker() as session:
        run = await run_repository.get_by_id(
            session,
            run_id,
        )

        if run is None:
            raise ValueError(
                f"Run {run_id} not found."
            )

        if run.module_name != "moatlens":
            raise ValueError(
                f"Run {run_id} is not a MoatLens run."
            )

        if run.status != "failed":
            raise ValueError(
                f"Run {run_id} cannot be retried because "
                f"its status is '{run.status}'."
            )

        if not run.thread_id:
            raise ValueError(
                f"Run {run_id} has no checkpoint thread."
            )

        if run.candidate_id is None:
            raise ValueError(
                f"Run {run_id} has no candidate associated with it."
            )

        candidate_id = run.candidate_id
        thread_id = run.thread_id

        run.status = "running"
        run.failed_node = None
        run.error = None
        run.completed_at = None

        await session.commit()

    if checkpointer_module.checkpointer is None:
        raise RuntimeError(
            "LangGraph checkpointer is not initialized."
        )

    moatlens_graph = build_moatlens_graph(
        checkpointer_module.checkpointer
    )

    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    try:
        state = await moatlens_graph.ainvoke(
            None,
            config=config,
        )

        final_report = state["final_report"]

        async with sessionmaker() as session:
            await report_repository.create(
                session,
                candidate_id=candidate_id,
                run_id=run_id,
                report_type=ReportType.diligence,
                content=final_report,
            )
            await run_repository.update_status(
                session,
                run_id=run_id,
                status="completed",
                completed_at=datetime.utcnow(),
            )

        logger.info(
            "MoatLens retry completed for run %s",
            run_id,
        )

        return final_report

    except MoatlensNodeError as exc:
        async with sessionmaker() as session:
            await run_repository.update_failure(
                session,
                run_id=run_id,
                failed_node=exc.node_name,
                error=str(exc.original_error),
            )

        logger.exception(
            "MoatLens retry failed at node %s",
            exc.node_name,
        )

        raise

    except Exception as exc:
        async with sessionmaker() as session:
            await run_repository.update_failure(
                session,
                run_id=run_id,
                failed_node="unknown",
                error=str(exc),
            )

        logger.exception(
            "MoatLens retry failed for run %s",
            run_id,
        )

        raise