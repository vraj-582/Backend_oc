from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.routers.chat import router as chat_router
from app.routers.auth import router as auth_router
from app.config import settings
from app.database import engine
from app import models

# Create DB tables on startup
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Enterprise Research Assistant API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(chat_router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


# ── Static file serving (production) ─────────────────────────
# CI/CD copies the built React app into backend/static/.
# In local dev this directory won't exist, so this is a no-op.

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

if STATIC_DIR.is_dir():
    # Serve Vite-built JS/CSS bundles
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    # SPA catch-all: serve static files or index.html for client-side routing
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = STATIC_DIR / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")
