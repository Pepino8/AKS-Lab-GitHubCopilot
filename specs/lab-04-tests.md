# Lab 04 — Test Pyramid & Continuous Integration Spec

## Goal

Establish a comprehensive test pyramid for the ZavaShop multi-agent fleet. The test suite verifies agent behavior under simulated LLM responses, isolates MCP tool logic with direct Pydantic calls, exercises A2A inter-agent integration over in-process ASGI transports without external network dependencies, evaluates whole-fleet business outcomes against golden scenarios, and gates all changes through GitHub Actions CI.

## Test Pyramid Layers

1. **Unit Tests (Agents)**: Per-agent unit tests in `tests/agents/<agent>/test_agent.py` exercising happy paths, domain refusal rules, and error propagation using `MockChatClient`.
2. **MCP Tool Tests**: Direct unit tests in `tests/mcp_servers/<mcp>/test_tools.py` invoking each tool with valid and invalid Pydantic models.
3. **Integration Tests (ASGI Loopback)**: In-process loopback tests in `tests/integration/test_fleet.py` using `httpx.ASGITransport` to exercise `/plan` and `/invoke` end-to-end without real HTTP servers or live Copilot tokens.
4. **Golden Eval Scenarios**: 5 end-to-end evaluation scenarios in `tests/evals/scenarios.jsonl` verified by `tests/evals/run_evals.py`.
5. **Quality Gates & CI**: Automated checks in `pyproject.toml` (`uv run poe check`, `uv run poe audit`, `uv run poe evals`) executed in GitHub Actions (`.github/workflows/ci.yml`).

## Acceptance Criteria

### Layer 1: Unit Tests (Agents)
- Each of the 5 agents (`inventory`, `supplier`, `logistics`, `pricing`, `orchestrator`) has unit tests verifying:
  1. Happy path: correct tool/MCP invocation and keyword presence in output.
  2. Domain refusal: explicit rejection of out-of-scope requests (e.g., inventory refusing supplier negotiation).
  3. Error propagation: proper surfacing of MCP or network failures without silent crashes.
- Tests patch `GitHubCopilotAgent` at the import site; no real Copilot CLI runs during unit testing.

### Layer 2: MCP Tool Tests
- Direct test files exist under `tests/mcp_servers/`:
  - `inventory/test_tools.py`: Tests `check_stock`.
  - `supplier/test_tools.py`: Tests `list_suppliers` and `draft_po`.
  - `shipping/test_tools.py`: Tests `quote_shipment`.
  - `pricing/test_tools.py`: Tests `recommend_price`.
- Each tool is tested with valid inputs and verified to return properly typed Pydantic models.

### Layer 3: Integration Tests (ASGI Loopback)
- `tests/integration/test_fleet.py` mounts the FastAPI apps (`orchestrator` and specialists) using `ASGITransport`.
- Tests verify:
  1. `POST /plan` produces a complete, structured `Plan` containing all specialist views.
  2. `POST /invoke` executes end-to-end flow with mocked LLM responses.

### Layer 4: Golden Evals
- `tests/evals/scenarios.jsonl` contains at least 5 scenarios:
  1. `stockout-zs1042-store101`: Standard stock-out recovery for store 101.
  2. `stockout-transfer-and-po`: Comparison of transfer vs. supplier replenishment.
  3. `stockout-price-protection`: Margin and price protection under critical stock risk.
  4. `stockout-supplier-delay`: Handling delayed supplier lead times.
  5. `stockout-demand-spike`: Mitigating sudden demand surges with expedited shipping.

### Layer 5: CI Quality Gate
- `pyproject.toml` provides tasks: `check`, `audit`, and `evals`.
- `.github/workflows/ci.yml` runs on push and pull_request to validate formatting, type safety (pyright), and test suites.

## Handoff

Handoff to `test-author`:
Implement `tests/mcp_servers/`, `tests/integration/`, 5 golden scenarios in `tests/evals/scenarios.jsonl`, and configure `ci.yml`.
