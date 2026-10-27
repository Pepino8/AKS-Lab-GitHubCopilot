"""Direct tool tests for the shipping MCP server."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.mcp_servers.shipping.models import ShipmentQuoteRequest
from src.mcp_servers.shipping.server import quote_shipment


@pytest.mark.asyncio
async def test_quote_shipment_happy_path() -> None:
    request = ShipmentQuoteRequest(po_id="PO-12345", destination_store_id="store-101", quantity=80)
    quote = await quote_shipment(request)

    assert quote.po_id == "PO-12345"
    assert quote.destination_store_id == "store-101"
    assert quote.cost > 0
    assert quote.eta_days >= 1
    assert "store-101" in quote.recommendation


@pytest.mark.asyncio
async def test_quote_shipment_unknown_store() -> None:
    request = ShipmentQuoteRequest(po_id="PO-12345", destination_store_id="unknown-destination", quantity=80)
    quote = await quote_shipment(request)

    assert quote.destination_store_id == "unknown-destination"
    assert quote.carrier == "Manual Dispatch Desk"


def test_quote_shipment_validation_error() -> None:
    with pytest.raises(ValidationError):
        ShipmentQuoteRequest(po_id="", destination_store_id="store-101", quantity=0)
