"""Deterministic plan workflow for the ZavaShop orchestrator."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import structlog

from .contracts import Goal, Plan

if TYPE_CHECKING:
    from .a2a import SpecialistInvoker

log = structlog.get_logger(__name__).bind(service="orchestrator-workflow")


async def run_plan_workflow(*, client: SpecialistInvoker, goal: Goal) -> Plan:
    """Execute the deterministic stock-out response workflow.

    Topology:
      1. Concurrent execution: check stock risk (inventory) and evaluate pricing (pricing).
      2. Sequential execution: list suppliers & draft purchase order (supplier).
      3. Sequential execution: quote shipment for replenishment (logistics).
      4. Reconcile specialist outputs into a structured Plan.
    """
    log.info("workflow.start", sku=goal.sku, store_id=goal.store_id)

    inventory_goal = (
        f"Check stock risk for SKU {goal.sku} at {goal.store_id}; include nearby store and warehouse options."
    )
    pricing_goal = (
        f"Recommend price for SKU {goal.sku} at {goal.store_id} with high demand signal and critical stock risk."
    )

    # Step 1: Run inventory and pricing concurrently
    async with asyncio.TaskGroup() as tg:
        inventory_task = tg.create_task(
            client.invoke(name="inventory", url=client.settings.inventory_a2a_url, goal=inventory_goal)
        )
        pricing_task = tg.create_task(
            client.invoke(name="pricing", url=client.settings.pricing_a2a_url, goal=pricing_goal)
        )

    stock_view = inventory_task.result()
    price_view = pricing_task.result()

    # Step 2: Run supplier evaluation
    supplier_goal = f"List suppliers and draft a purchase order for SKU {goal.sku} at {goal.store_id} quantity 80."
    po_view = await client.invoke(name="supplier", url=client.settings.supplier_a2a_url, goal=supplier_goal)

    # Step 3: Run logistics shipment quote
    shipping_goal = f"Quote shipment for PO candidate for {goal.sku} at {goal.store_id} to {goal.store_id} quantity 80."
    shipping_view = await client.invoke(name="logistics", url=client.settings.logistics_a2a_url, goal=shipping_goal)

    # Step 4: Reconcile into Plan
    log.info("workflow.reconciled", sku=goal.sku, store_id=goal.store_id)
    return Plan(
        sku=goal.sku,
        store_id=goal.store_id,
        stock_view=stock_view,
        po_view=po_view,
        shipping_view=shipping_view,
        price_view=price_view,
        summary=(
            f"Recovery plan for {goal.sku} at {goal.store_id}: protect stock, place replenishment, "
            "ship quickly, and tune price during the stock-out window."
        ),
        next_actions=[
            "Approve the recommended replenishment purchase order.",
            "Book the recommended shipment to the target store.",
            "Apply the price recommendation until stock risk clears.",
        ],
    )
