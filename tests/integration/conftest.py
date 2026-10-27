"""Integration test fixtures using in-process ASGI loopback transports."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import AsyncExitStack
from dataclasses import dataclass

import httpx
import pytest
from httpx import ASGITransport

from src.agents.inventory.server import app as inventory_app
from src.agents.logistics.server import app as logistics_app
from src.agents.orchestrator.server import create_app as create_orchestrator_app
from src.agents.pricing.server import app as pricing_app
from src.agents.supplier.server import app as supplier_app
from src.shared.settings import Settings
from tests.agents._mock import MockChatClient


@dataclass(frozen=True)
class ASGISpecialistClient:
    clients: dict[str, httpx.AsyncClient]
    settings: Settings

    async def invoke(self, *, name: str, url: str, goal: str, run_id: str | None = None) -> str:
        client = self.clients[name]
        response = await client.post("/invoke", json={"run_id": run_id or "r-test", "goal": goal})
        response.raise_for_status()
        return response.json()["output"]


@pytest.fixture
async def fleet(monkeypatch: pytest.MonkeyPatch) -> AsyncGenerator[dict[str, httpx.AsyncClient], None]:
    """Mount all fleet FastAPI apps behind ASGITransport with mocked Copilot agents."""
    MockChatClient.reset(
        responses=[
            (
                '{"sku":"ZS-1042","store_id":"store-101","stock_view":"stock critical",'
                '"risk_level":"critical","recommendation":"transfer from store-202"}'
            ),
            (
                '{"sku":"ZS-1042","current_price":39.99,"recommended_price":42.79,'
                '"margin_impact":"+$2.80","rationale":"protect scarce inventory"}'
            ),
            (
                '{"sku":"ZS-1042","supplier_id":"sup-northstar","po_id":"PO-12345",'
                '"eta_days":4,"estimated_total":1875.0,"status":"draft"}'
            ),
            (
                '{"po_id":"PO-12345","carrier":"Fabrikam RapidShip","eta_days":1,'
                '"cost":435.0,"recommendation":"same-day expedite"}'
            ),
            '{"plan":"recovery plan created"}',
        ]
    )

    for mod in (
        "src.agents.inventory.agent",
        "src.agents.supplier.agent",
        "src.agents.logistics.agent",
        "src.agents.pricing.agent",
        "src.agents.orchestrator.agent",
    ):
        monkeypatch.setattr(f"{mod}.GitHubCopilotAgent", MockChatClient)

    settings = Settings(
        inventory_a2a_url="http://inventory/invoke",
        supplier_a2a_url="http://supplier/invoke",
        logistics_a2a_url="http://logistics/invoke",
        pricing_a2a_url="http://pricing/invoke",
    )

    clients: dict[str, httpx.AsyncClient] = {
        "inventory": httpx.AsyncClient(transport=ASGITransport(app=inventory_app), base_url="http://inventory"),
        "supplier": httpx.AsyncClient(transport=ASGITransport(app=supplier_app), base_url="http://supplier"),
        "logistics": httpx.AsyncClient(transport=ASGITransport(app=logistics_app), base_url="http://logistics"),
        "pricing": httpx.AsyncClient(transport=ASGITransport(app=pricing_app), base_url="http://pricing"),
    }

    specialist_client = ASGISpecialistClient(clients=clients, settings=settings)
    orchestrator_app = create_orchestrator_app(settings=settings, specialist_client=specialist_client)
    clients["orchestrator"] = httpx.AsyncClient(
        transport=ASGITransport(app=orchestrator_app), base_url="http://orchestrator"
    )

    apps = [inventory_app, supplier_app, logistics_app, pricing_app, orchestrator_app]
    async with AsyncExitStack() as stack:
        for app in apps:
            await stack.enter_async_context(app.router.lifespan_context(app))
        yield clients

    for client in clients.values():
        await client.aclose()
