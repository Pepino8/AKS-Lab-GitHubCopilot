"""Direct tool tests for the pricing MCP server."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.mcp_servers.pricing.models import PricingQuery
from src.mcp_servers.pricing.server import recommend_price


@pytest.mark.asyncio
async def test_recommend_price_happy_path() -> None:
    query = PricingQuery(sku="ZS-1042", store_id="store-101", demand_signal="high", stock_risk_level="critical")
    rec = await recommend_price(query)

    assert rec.sku == "ZS-1042"
    assert rec.store_id == "store-101"
    assert rec.recommended_price > 0
    assert "Estimated unit margin" in rec.margin_impact
    assert "demand signal" in rec.rationale


@pytest.mark.asyncio
async def test_recommend_price_unknown_sku() -> None:
    query = PricingQuery(sku="UNKNOWN-SKU", store_id="store-101", demand_signal="low", stock_risk_level="low")
    rec = await recommend_price(query)

    assert rec.sku == "UNKNOWN-SKU"
    assert rec.recommended_price > 0


def test_recommend_price_validation_error() -> None:
    with pytest.raises(ValidationError):
        PricingQuery(sku="", store_id="store-101", demand_signal="", stock_risk_level="")
