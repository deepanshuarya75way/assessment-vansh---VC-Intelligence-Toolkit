from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.candidates import router as candidates_router
from app.api.corridor import router as corridor_router
from app.api.history import router as history_router
from app.api.moatlens import router as moatlens_router
from app.api.navigator import router as navigator_router
from app.api.reports import router as reports_router
from app.core.config import settings
from app.utils.logger import get_logger
from app.database.checkpointer import init_checkpointer, close_checkpointer

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Together Intelligence Toolkit backend starting")
    logger.debug("Configured model: %s", settings.model_name)

    await init_checkpointer()

    yield

    await close_checkpointer()


app = FastAPI(title="VC Intelligence Toolkit", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173","https://vc-intelligence-toolkit.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(corridor_router)
app.include_router(candidates_router)
app.include_router(moatlens_router)
app.include_router(navigator_router)
app.include_router(history_router)
app.include_router(reports_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
