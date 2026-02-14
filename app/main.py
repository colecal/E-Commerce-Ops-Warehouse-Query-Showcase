from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.api.routes import router

BASE_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = BASE_DIR / "frontend" / "public"

app = FastAPI(title="E-Commerce Ops Warehouse Query Showcase", version="0.1.0")

app.include_router(router, prefix="/api")

# Serve the simple frontend (local demo)
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


@app.get("/app")
def app_entry():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"ok": True, "note": "frontend not found"}
