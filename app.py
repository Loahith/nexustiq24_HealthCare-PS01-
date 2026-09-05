"""
NexusTiq24 Hackathon - PS01 Healthcare Patient Intake Triage Assistant

Run with:
    python app.py

Serves the API and the built React frontend (frontend/dist) together on
http://localhost:8000 - no separate frontend command required.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

load_dotenv()

from src.utils.logger import setup_logging  # noqa: E402

setup_logging(logging.INFO)
logger = logging.getLogger("nexustiq24.app")

from src.database.db import init_db  # noqa: E402
from src.api.routes import router as api_router  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

app = FastAPI(
    title="NexusTiq24 Patient Intake Triage Assistant",
    description="Rule-based, RAG-augmented patient intake triage assistant. Never diagnoses.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.on_event("startup")
def on_startup() -> None:
    Path("data/generated_reports").mkdir(parents=True, exist_ok=True)
    init_db()
    logger.info("Database initialized.")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.exists() and candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(FRONTEND_DIST / "index.html"))
else:
    logger.warning(
        "frontend/dist not found. Run `npm install && npm run build` inside frontend/ "
        "before starting, or the app will only serve the API."
    )


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    logger.info("Starting NexusTiq24 Triage Assistant on http://localhost:%s", port)
    uvicorn.run("app:app", host=host, port=port, reload=False)
