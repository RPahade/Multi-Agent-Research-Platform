"""Aggregates all v1 API routers into a single router mounted by the app.

New feature routers (documents, research, chat, auth, ...) get included here in
their respective milestones, keeping ``main.py`` free of route wiring.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes import agents, auth, health, reports, tools, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(agents.router)
api_router.include_router(tools.router)
api_router.include_router(reports.router)
