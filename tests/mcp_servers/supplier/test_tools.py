"""Direct tool tests for the supplier MCP server."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.mcp_servers.supplier.models import PurchaseOrderRequest, SupplierQuery
from src.mcp_servers.supplier.server import draft_po, list_suppliers

TEST_ORDER_QTY = 50


@pytest.mark.asyncio
async def test_list_suppliers_happy_path() -> None:
    query = SupplierQuery(sku="ZS-1042")
    result = await list_suppliers(query)

    assert result.sku == "ZS-1042"
    assert len(result.suppliers) >= 1
    assert any(s.supplier_id == "sup-northstar" for s in result.suppliers)


@pytest.mark.asyncio
async def test_list_suppliers_unknown_sku() -> None:
    query = SupplierQuery(sku="UNKNOWN-SKU")
    result = await list_suppliers(query)

    assert result.sku == "UNKNOWN-SKU"
    assert result.suppliers == []


@pytest.mark.asyncio
async def test_draft_po_happy_path() -> None:
    request = PurchaseOrderRequest(
        sku="ZS-1042", store_id="store-101", supplier_id="sup-northstar", quantity=TEST_ORDER_QTY
    )
    draft = await draft_po(request)

    assert draft.po_id.startswith("PO-")
    assert draft.sku == "ZS-1042"
    assert draft.store_id == "store-101"
    assert draft.supplier_id == "sup-northstar"
    assert draft.quantity == TEST_ORDER_QTY
    assert draft.estimated_total > 0
    assert draft.status == "draft"


def test_supplier_validation_errors() -> None:
    with pytest.raises(ValidationError):
        SupplierQuery(sku="")

    with pytest.raises(ValidationError):
        PurchaseOrderRequest(sku="ZS-1042", store_id="store-101", supplier_id="sup-northstar", quantity=0)
