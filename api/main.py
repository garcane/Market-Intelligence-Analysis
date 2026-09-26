"""FastAPI entry point for the AI Market Intelligence web app.

Dev:   uvicorn api.main:app --reload            (React dev server proxies /api here)
Prod:  build web/ first (npm run build); this app then serves web/dist too.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api import data
from api.deps import LOCAL_HOSTS, get_settings
from api.routers import markets, models, pipeline, reference, sentiment
from api.settings import Settings, load_settings
from src.config import ROOT_DIR

WEB_DIST = ROOT_DIR / "web" / "dist"


def create_app(mode: str | None = None, web_dist: Path = WEB_DIST) -> FastAPI:
    settings = load_settings(mode)
    public = settings.public
    app = FastAPI(title="AI Market Intelligence API", version="1.0.0",
                  docs_url=None if public else "/api/docs", redoc_url=None, openapi_url=None if public else "/api/openapi.json")
    app.state.settings = settings
    app.state.local_hosts = set(LOCAL_HOSTS)

    app.add_middleware(GZipMiddleware, minimum_size=1024)
    if settings.allowed_origins:
        app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins,
                           allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

    for router in (markets.router, reference.router, sentiment.router, models.router):
        app.include_router(router)
    if settings.pipeline_enabled:
        app.include_router(pipeline.router)

    @app.get("/api/meta", tags=["meta"])
    def meta(s: Settings = Depends(get_settings)) -> dict:
        ids = data.market_ids()
        latest = [str(df["date"].max().date()) for i in ids
                  if (df := data.market_prices(i, s.excluded_sources)) is not None and not df.empty]
        news, sent = data.news(), data.sentiment()
        return data.clean({
            "mode": s.mode,
            "pipeline_enabled": s.pipeline_enabled,
            "market_ids": ids,
            "latest_price_date": max(latest) if latest else None,
            "news_count": 0 if news is None else len(news),
            "latest_news": None if news is None or news.empty else news["timestamp"].max().isoformat(),
            "scored_articles": 0 if sent is None else int(sent["news_id"].nunique()),
        })

    @app.get("/api/health", tags=["meta"])
    def health() -> dict:
        return {"status": "ok"}

    if (web_dist / "index.html").exists():
        _mount_frontend(app, web_dist)
    return app


def _mount_frontend(app: FastAPI, web_dist: Path) -> None:
    """Serve the built React app, falling back to index.html for client-side routes."""
    if (web_dist / "assets").exists():
        app.mount("/assets", StaticFiles(directory=web_dist / "assets"), name="assets")
    root = web_dist.resolve()

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        if path.startswith("api/"):
            raise HTTPException(404, "not found")
        candidate = (web_dist / path).resolve()
        if path and candidate.is_file() and root in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(web_dist / "index.html", headers={"Cache-Control": "no-cache"})


app = create_app()
