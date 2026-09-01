from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.db import engine
from backend.models import Base
from backend.routers import auth as auth_router
from backend.routers import state as state_router

DIST_PATH = Path(__file__).parent.parent / "dist"
DIST_FILES = StaticFiles(directory=DIST_PATH, check_dir=False)


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

@app.get("/{full_path:path}")
async def serve_root(full_path: str, request: Request):
    """Serve a static file if it exists, otherwise fall back to root index.html."""
    if full_path:
        if ".." in full_path.replace("\\", "/").split("/"):
            raise HTTPException(status_code=404)
        try:
            response = await DIST_FILES.get_response(full_path, request.scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404:
                raise
        else:
            if response.status_code != 404:
                return response
    index = DIST_PATH / "index.html"
    if index.exists():
        return FileResponse(index)
    return JSONResponse(
        {"error": "Frontend not built. Run: npm run build"},
        status_code=503,
    )
