"""Integration tests exercising the fleet over in-process ASGI loopback transports."""

from __future__ import annotations

from http import HTTPStatus

import httpx
import pytest


@pytest.mark.asyncio
async def test_fleet_plan_endpoint_loopback(fleet: dict[str, httpx.AsyncClient]) -> None:
    orchestrator = fleet["orchestrator"]
    response = await orchestrator.post(
        "/plan",
        json={
            "goal": "Store 101 will stock out of SKU ZS-1042 by Friday.",
            "sku": "ZS-1042",
            "store_id": "store-101",
        },
    )

    assert response.status_code == HTTPStatus.OK
    plan = response.json()
    assert plan["sku"] == "ZS-1042"
    assert plan["store_id"] == "store-101"
    assert "stock_view" in plan
    assert "price_view" in plan
    assert "po_view" in plan
    assert "shipping_view" in plan
    assert "next_actions" in plan


@pytest.mark.asyncio
async def test_fleet_specialist_invoke_endpoints(fleet: dict[str, httpx.AsyncClient]) -> None:
    for client in fleet.values():
        response = await client.get("/healthz")
        assert response.status_code == HTTPStatus.OK
        assert response.json() == {"status": "ok"}
