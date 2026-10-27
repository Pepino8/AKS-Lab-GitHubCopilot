"""Direct tool tests for the inventory MCP server."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.mcp_servers.inventory.models import StockQuery
from src.mcp_servers.inventory.server import check_stock


@pytest.mark.asyncio
async def test_check_stock_happy_path() -> None:
    query = StockQuery(sku="ZS-1042", store_id="store-101")
    report = await check_stock(query)

    assert report.sku == "ZS-1042"
    assert report.store_id == "store-101"
    assert report.risk_level in {"critical", "high"}
    assert report.target.location_id == "store-101"
    assert len(report.nearby_locations) >= 1
    assert "store-101" in report.recommendation


@pytest.mark.asyncio
async def test_check_stock_unknown_sku() -> None:
    query = StockQuery(sku="UNKNOWN-SKU", store_id="store-101")
    report = await check_stock(query)

    assert report.sku == "UNKNOWN-SKU"
    assert report.risk_level == "unknown"
    assert "No inventory record exists" in report.recommendation


def test_check_stock_invalid_inputs() -> None:
    with pytest.raises(ValidationError):
        StockQuery(sku="", store_id="store-101")
