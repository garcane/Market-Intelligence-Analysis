"""Shared FastAPI dependencies."""
from __future__ import annotations

from fastapi import HTTPException, Request

from api.settings import Settings

LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost"}


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def require_local(request: Request) -> None:
    """Pipeline runs spend API quotas and write data: only the machine the
    server runs on may start them, and only in local mode."""
    settings: Settings = request.app.state.settings
    host = request.client.host if request.client else None
    if not settings.pipeline_enabled or host not in request.app.state.local_hosts:
        raise HTTPException(403, "pipeline runs are only allowed from localhost in local mode")
