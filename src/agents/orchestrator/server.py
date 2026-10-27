"""FastAPI entrypoint for the ZavaShop orchestrator agent."""

from __future__ import annotations

from fastapi import FastAPI

from src.shared.server import make_app
from src.shared.settings import Settings

from .a2a import SpecialistClient, SpecialistInvoker
from .agent import build_agent
from .contracts import Goal, Plan
from .workflow import run_plan_workflow


def create_app(settings: Settings | None = None, specialist_client: SpecialistInvoker | None = None) -> FastAPI:
    """Create the orchestrator app with /invoke and /plan endpoints."""

    app_settings = settings or Settings()
    app = make_app(name="orchestrator", build=build_agent, settings=app_settings)
    client = specialist_client or SpecialistClient(settings=app_settings)

    @app.post("/plan", response_model=Plan)
    async def plan(goal: Goal) -> Plan:
        return await run_plan_workflow(client=client, goal=goal)

    app.state.plan_endpoint = plan

    return app


app = create_app()
