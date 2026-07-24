from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from app.api.health import router as health_router
from app.api.piloto import router as piloto_router
from app.config import get_settings

settings = get_settings()
STATIC_DIR = Path(__file__).resolve().parent / "static" / "piloto"

app = FastAPI(
    title=settings.app_name,
    version="0.5.1",
    description=(
        "API OCR de códigos de equipos. "
        "Fase 0.5 HITL: /ui — validación humana → dataset Fase 0."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(piloto_router, prefix=settings.api_prefix)

if STATIC_DIR.is_dir():
    app.mount("/ui", StaticFiles(directory=str(STATIC_DIR), html=True), name="piloto-ui")


@app.on_event("startup")
def ensure_storage() -> None:
    root = Path(settings.storage_path)
    (root / "originals").mkdir(parents=True, exist_ok=True)
    (root / "thumbs").mkdir(parents=True, exist_ok=True)
    (root / "piloto").mkdir(parents=True, exist_ok=True)
    Path(settings.dataset_path).mkdir(parents=True, exist_ok=True)
    (Path(settings.dataset_path) / "images").mkdir(parents=True, exist_ok=True)


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/ui/")


@app.get("/api")
def api_info() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "docs": "/docs",
        "ui": "/ui/",
        "health": f"{settings.api_prefix}/health",
        "piloto_analizar": f"{settings.api_prefix}/piloto/analizar",
        "piloto_validar": f"{settings.api_prefix}/piloto/validar",
        "phase": "0.5",
    }


@app.get("/favicon.ico")
def favicon() -> Response:
    return Response(status_code=204)
