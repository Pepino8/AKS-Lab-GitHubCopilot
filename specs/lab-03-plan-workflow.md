# Lab 03 — Plan Workflow & Configuration Spec

## Goal

Implement a deterministic, non-LLM `/plan` workflow in the ZavaShop orchestrator and enable Azure Key Vault secret hydration across all fleet services. Given a stock-out `Goal(goal, sku, store_id)`, the orchestrator executes a typed, auditable multi-agent workflow over A2A HTTP: executing stock risk and pricing evaluation in parallel, followed by supplier purchase order drafting, shipping quoting, and final reconciliation into a structured `Plan`. In addition, hydrate secrets from Azure Key Vault at startup when `ZAVA_KV_URL` is set.

## Non-goals

- Do not use free-form LLM generation for `/plan`; the plan flow is a deterministic, typed workflow.
- Do not make direct in-process calls to specialist implementations; all agent communication must use A2A HTTP.
- Do not overwrite existing environment variables during Key Vault hydration.
- Do not hardcode or commit secret tokens to source code or git history.

## Personas

- **Store Manager**: Needs immediate, structured guidance on a store-level stock-out without nondeterministic hallucinations.
- **Supply Chain Director**: Demands traceable, auditable step-by-step logic linking stock verification, PO drafting, shipment quotes, and price adjustments.
- **Platform Engineer**: Requires uniform startup hydration of secrets from Azure Key Vault across both AKS and ACA topologies.

## Affected agents & components

- [x] `src/agents/orchestrator/workflow.py` — deterministic DAG execution logic.
- [x] `src/agents/orchestrator/server.py` — expose POST `/plan` endpoint returning frozen `Plan`.
- [x] `src/shared/keyvault.py` — async Key Vault secret hydration helper.
- [x] `src/agents/*/server.py` — call hydration on startup when `ZAVA_KV_URL` is present.
- [x] `src/mcp_servers/*/server.py` — call hydration on startup when `ZAVA_KV_URL` is present.
- [x] `docker-compose.yml` — fleet deployment definitions with health checks and timeout configurations.

## Workflow Topology

```text
               +-----------------------+
               |  Goal(sku, store_id)  |
               +-----------+-----------+
                           |
             +-------------+-------------+
             |                           |
             v                           v
     +---------------+           +---------------+
     | ask_inventory |           |  ask_pricing  |
     +-------+-------+           +-------+-------+
             |                           |
             +-------------+-------------+
                           |
                           v
                   +----------------+
                   |  ask_supplier  |
                   +-------+--------+
                           |
                           v
                   +----------------+
                   |  ask_logistics |
                   +-------+--------+
                           |
                           v
                   +----------------+
                   | Reconcile Plan |
                   +----------------+
```

## Contracts

```python
from pydantic import BaseModel, ConfigDict, Field


class Goal(BaseModel):
    model_config = ConfigDict(frozen=True)

    goal: str = Field(min_length=1)
    sku: str = Field(min_length=1)
    store_id: str = Field(min_length=1)


class Plan(BaseModel):
    model_config = ConfigDict(frozen=True)

    sku: str
    store_id: str
    stock_view: str
    price_view: str
    po_view: str
    shipping_view: str
    summary: str
    next_actions: list[str]
```

## Acceptance Criteria

1. **POST `/plan` Endpoint**: Accepts `Goal` and returns a frozen `Plan` containing `sku`, `store_id`, `stock_view`, `price_view`, `po_view`, `shipping_view`, `summary`, and `next_actions`.
2. **Parallel Stock & Pricing Execution**: The workflow invokes inventory and pricing evaluation concurrently, followed by supplier PO drafting and shipping quoting.
3. **Resilient Timeouts**: All A2A HTTP client invocations use `httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=10.0)`.
4. **Key Vault Hydration**: `src/shared/keyvault.py` uses `azure.keyvault.secrets.aio.SecretClient` with `DefaultAzureCredential` to fetch `GITHUB-TOKEN` and `*_MCP_URL` secrets when `ZAVA_KV_URL` is defined, without overwriting existing environment variables, and closes credentials cleanly in a `finally` block.
5. **Universal Wiring**: All 9 fleet server endpoints (5 agents + 4 MCP servers) call `hydrate_from_keyvault` on startup.

## Eval Scenarios

```jsonl
{"id":"eval-plan-zs1042-store101","goal":"Store 101 will stock out of SKU ZS-1042 by Friday. Build a recovery plan for store-101.","sku":"ZS-1042","store_id":"store-101","must_mention":["ZS-1042","store-101","stock","purchase order","shipping","price"],"must_call":["inventory","supplier","logistics","pricing"],"forbid_call":[],"max_latency_s":120}
{"id":"eval-plan-transfer-and-po","goal":"Compare nearby stock with supplier replenishment for ZS-1042 at store-101.","sku":"ZS-1042","store_id":"store-101","must_mention":["store-202","wh-east","supplier","ETA","next actions"],"must_call":["inventory","supplier","logistics","pricing"],"forbid_call":[],"max_latency_s":120}
```

## Out of Scope

- Human-in-the-loop approval gates before PO submission.
- Real-time carrier rate calculation from live carrier APIs.
- Multi-store or regional routing in a single plan invocation.

## Handoff

Handoff to `orchestrator-architect`:
Implement `src/agents/orchestrator/workflow.py`, add `POST /plan` in `server.py`, create `src/shared/keyvault.py`, and wire Key Vault hydration across all 9 fleet services.
