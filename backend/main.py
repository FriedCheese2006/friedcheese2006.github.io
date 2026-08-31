from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from backend.db import engine
from backend.models import Base
from backend.routers import auth as auth_router
from backend.routers import state as state_router

DIST_PATH = Path(__file__).parent.parent / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-create tables on startup (idempotent)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None)

# Auth and API routes — registered before static file catch-alls
app.include_router(auth_router.router)
app.include_router(state_router.router)

# Mount Vite build output directories (served before catch-all routes)
if DIST_PATH.exists():
    if (DIST_PATH / "icarus-game").exists():
        app.mount(
            "/icarus-game",
            StaticFiles(directory=DIST_PATH / "icarus-game"),
            name="game-assets",
        )
    if (DIST_PATH / "assets").exists():
        app.mount(
            "/assets",
            StaticFiles(directory=DIST_PATH / "assets"),
            name="vite-assets",
        )


@app.get("/icarus")
@app.get("/icarus/{full_path:path}")
async def redirect_legacy_icarus_path(full_path: str = ""):
    """Redirect legacy /icarus URLs to root-based SPA paths."""
    target = f"/{full_path}" if full_path else "/"
    return RedirectResponse(url=target, status_code=308)


@app.get("/{full_path:path}")
async def serve_root(full_path: str):
    """Serve a static file if it exists, otherwise fall back to root index.html."""
    if full_path:
        dist_path = DIST_PATH.resolve()
        candidate = (dist_path / full_path).resolve()
        if not candidate.is_relative_to(dist_path):
            raise HTTPException(status_code=404)
        if candidate.is_file():
            return FileResponse(candidate)
    index = DIST_PATH / "index.html"
    if index.exists():
        return FileResponse(index)
    return JSONResponse(
        {"error": "Frontend not built. Run: npm run build"},
        status_code=503,
    )
