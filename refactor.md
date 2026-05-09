# YNAB MCP Server Refactor Plan

A FastMCP 3.0 best-practices audit revealed several places where the server is working *around* the framework instead of *with* it. This document captures the proposed refactor — start with the high-impact items, then tackle the structural reorganization (filesystem provider) that ties them together.

## High-impact issues

### 1. Replace manual token plumbing with `Depends()`

Every tool currently starts with this boilerplate (`app/tools.py:44-50`, repeated 9 times):

```python
token = get_access_token()
if not token:
    return {"error": "No valid authentication token found"}
access_token = token.token
service = YNABService(access_token)
```

Since the server is configured with `auth=auth_provider`, unauthenticated requests never reach a tool — the `if not token` branch is dead code. Use dependency injection so each tool just receives a configured `YNABService`:

```python
from fastmcp.dependencies import Depends, CurrentAccessToken
from fastmcp.server.auth import AccessToken

def get_ynab_service(token: AccessToken = CurrentAccessToken()) -> YNABService:
    return YNABService(token.token)

@tool
async def get_budgets(
    include_accounts: bool = False,
    service: YNABService = Depends(get_ynab_service),
) -> BudgetListResponse:
    ...
```

`Depends`-injected parameters are excluded from the LLM-facing schema. This deletes ~50 lines of boilerplate.

### 2. Raise `ToolError` instead of returning error dicts

Tools currently catch exceptions and return `{"error": "...", "status_code": 404}`. The MCP call *succeeds* with an error field, so the LLM has to learn the shape. The framework already has the right path:

```python
from fastmcp.exceptions import ToolError

except BudgetNotFoundException as e:
    raise ToolError(f"Budget {e.budget_id} not found")
```

Unhandled exceptions are converted to MCP errors automatically, so most try/except blocks can be deleted entirely. Only translate domain exceptions where the message needs friendlier wording.

### 3. Return typed Pydantic models instead of `dict`

Every tool returns `dict` and manually calls `.model_dump()`. With a return-type annotation, FastMCP auto-generates an output schema and produces both `content` and `structuredContent` (see `references/server/tools.md`). Define response models:

```python
class BudgetListResponse(BaseModel):
    budgets: list[BudgetSummary]
    count: int

@tool
async def get_budgets(...) -> BudgetListResponse:
    budgets = await service.get_budgets(...)
    return BudgetListResponse(budgets=budgets, count=len(budgets))
```

This documents the response shape for clients, deletes the manual `model_dump()` calls, and gives MCP clients deserializable structured data.

### 4. Use `Literal[...]` instead of runtime string checks

`update_transaction` validates `cleared` and `flag_color` against allowed strings at runtime (`tools.py:690-695`). Push validation into the type system:

```python
cleared: Literal["cleared", "uncleared", "reconciled"] | None = None
flag_color: Literal["red", "orange", "yellow", "green", "blue", "purple"] | None = None
```

The LLM sees the allowed values in the tool schema, Pydantic enforces them, and the runtime checks become dead code.

### 5. Remove `_log_registered_resources` (or move to a lifespan)

`app/main.py:26-27` calls `asyncio.run(mcp_server.list_tools())` during `mcp = create_mcp_server()` at import time. This breaks if the module is imported under a running event loop. FastMCP already logs registered tools — delete this debug helper, or move it into a `@lifespan` startup hook (`references/features/lifespans.md`).

### 6. Drop the `register_tools()` / `register_prompts()` indirection

Tools defined as nested functions inside `register_tools()` are harder to test and don't match any FastMCP example. The fix dovetails with the structural change below — once tools are in their own files using standalone `@tool` decorators, the indirection disappears entirely.

## Medium-impact issues

### 7. Share an `httpx.AsyncClient` via a lifespan

`services.py:42` creates a new `AsyncClient` on every `_make_request`. Move client creation into a lifespan and inject it:

```python
from fastmcp.server.lifespan import lifespan

@lifespan
async def http_client_lifespan(server):
    async with httpx.AsyncClient(timeout=config.request_timeout) as client:
        yield {"http_client": client}

mcp = FastMCP(..., lifespan=http_client_lifespan)
```

Then `YNABService` takes the shared client. Connection pools stay warm; latency drops materially.

### 8. Pass `instructions=` to `FastMCP`

`FastMCP(config.server_name, auth=auth_provider)` skips the `instructions` parameter. A short paragraph describing what the server does and when to call which tool helps clients route correctly.

### 9. Add `timeout=` to network-bound tools

Every tool calls YNAB over the network. `@tool(timeout=30.0, ...)` ensures clients get a clean MCP error instead of hanging when YNAB is slow.

### 10. Drop the JSON-string `payee_id` parsing

`tools.py:226-232` parses `payee_id` strings that look like JSON arrays. With `payee_id: list[str] | None = None` and FastMCP's flexible Pydantic validation, clients can send a real list. If this hack exists for a specific client, comment that explicitly; otherwise remove it.

### 11. Inject `Context` for logging and progress

`analyze_spending` makes multiple sequential API calls. Add `ctx: Context` and call `ctx.report_progress()` / `ctx.info()` so clients can show progress (`references/server/tools.md:954-992`).

### 12. Fix the hardcoded `scopes=["read-only"]` in `YNABTokenVerifier`

`auth.py:48` always claims read-only scope regardless of `YNAB_READ_ONLY`. Either reflect the real scope or drop the field — the current value is misleading.

### 13. Wire `YNAB_READ_ONLY` to tag-based filtering

Tools have `tags={"readonly", ...}` but they're never filtered on. If `YNAB_READ_ONLY=True` is supposed to gate `update_transaction`, that gating isn't actually happening:

```python
include_tags = {"readonly"} if config.YNAB_READ_ONLY else None
mcp = FastMCP(..., include_tags=include_tags)
```

## Lower-priority

- Modernize `Optional[str]` → `str | None` (Python 3.10+ already required).
- Consider `mask_error_details=True` for production deployments.
- Expose budgets/accounts as MCP **resources** (`ynab://budgets/{id}`) so clients can browse data without a tool call.

## Structural change: filesystem provider

The current `app/tools.py` is one 716-line file with nine tools defined as nested functions. Splitting them into per-tool files becomes natural with `FileSystemProvider` — each file is self-contained and uses standalone decorators (`@tool`, `@resource`, `@prompt` from `fastmcp.tools` / `.resources` / `.prompts`) that don't reference the server instance.

### Proposed directory layout

```
app/
├── __init__.py
├── auth.py
├── config.py
├── dependencies.py        # get_ynab_service, shared Depends helpers
├── exceptions.py
├── main.py                # FastMCP(...) + FileSystemProvider wiring
├── models/                # existing pydantic models
├── responses.py           # NEW: typed response models for tool outputs
├── services.py
└── mcp/                   # discovered by FileSystemProvider
    ├── __init__.py        # enables relative imports from app.*
    ├── tools/
    │   ├── budgets.py     # get_budgets, get_budget
    │   ├── accounts.py    # get_accounts, get_account
    │   ├── transactions.py  # get_transactions, update_transaction
    │   ├── categories.py  # get_categories
    │   ├── payees.py      # get_payees, find_payee_by_name
    │   └── analytics.py   # analyze_spending
    └── prompts/
        ├── budget_summary.py
        ├── spending_analysis.py
        ├── budget_setup.py
        └── debt_analysis.py
```

The `__init__.py` inside `app/mcp/` lets each tool file use relative imports to reach shared code (`from ...services import YNABService`, `from ...dependencies import get_ynab_service`).

### What `app/main.py` looks like after

```python
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.providers import FileSystemProvider
from fastmcp.server.auth import OAuthProxy

from app.auth import YNABTokenVerifier
from app.config import config

token_verifier = YNABTokenVerifier()

auth_provider = OAuthProxy(
    upstream_authorization_endpoint="https://app.ynab.com/oauth/authorize",
    upstream_token_endpoint="https://app.ynab.com/oauth/token",
    upstream_client_id=config.YNAB_CLIENT_ID,
    upstream_client_secret=config.YNAB_CLIENT_SECRET.get_secret_value(),
    token_verifier=token_verifier,
    base_url=config.YNAB_BASE_URL,
    redirect_path="/oauth/callback",
    issuer_url=config.YNAB_BASE_URL,
)

mcp = FastMCP(
    config.server_name,
    instructions="Provides read/write access to YNAB budgets, accounts, transactions, categories, and payees. Use the read-only tools to inspect a budget and `update_transaction` to add memos or recategorize.",
    auth=auth_provider,
    providers=[FileSystemProvider(Path(__file__).parent / "mcp")],
    include_tags={"readonly"} if config.YNAB_READ_ONLY else None,
)
```

That's the whole server file. No `register_tools()`, no nested closures, no module-load asyncio gymnastics.

### What a tool file looks like

```python
# app/mcp/tools/budgets.py
from fastmcp.tools import tool
from fastmcp.dependencies import Depends

from ...dependencies import get_ynab_service
from ...exceptions import BudgetNotFoundException
from ...responses import BudgetListResponse, BudgetResponse
from ...services import YNABService
from fastmcp.exceptions import ToolError

@tool(
    tags={"budget", "readonly"},
    annotations={"title": "Get All Budgets", "readOnlyHint": True},
    timeout=30.0,
)
async def get_budgets(
    include_accounts: bool = False,
    service: YNABService = Depends(get_ynab_service),
) -> BudgetListResponse:
    """Get all budgets for the authenticated user."""
    budgets = await service.get_budgets(include_accounts=include_accounts)
    return BudgetListResponse(budgets=budgets, count=len(budgets))


@tool(
    tags={"budget", "readonly"},
    annotations={"title": "Get Budget Details", "readOnlyHint": True},
    timeout=30.0,
)
async def get_budget(
    budget_id: str = "last-used",
    service: YNABService = Depends(get_ynab_service),
) -> BudgetResponse:
    """Get detailed information for a specific budget."""
    try:
        return await service.get_budget(budget_id)
    except BudgetNotFoundException as e:
        raise ToolError(f"Budget {e.budget_id} not found")
```

Compare that to today's nested-closure version of the same two tools (`tools.py:24-91`) — about a third of the lines, no manual token handling, no error-dict envelopes, no `model_dump()`.

### What a prompt file looks like

```python
# app/mcp/prompts/budget_summary.py
from fastmcp.prompts import prompt

@prompt(name="budget_summary")
async def budget_summary_prompt(budget_id: str = "last-used") -> str:
    """Generate a prompt for comprehensive budget summary analysis."""
    return f"""..."""  # template body
```

### Migration order

Doing this in one go is risky. Suggested sequence:

1. Add `app/responses.py` with typed response models. Land this without touching tools.
2. Add `app/dependencies.py` with `get_ynab_service`. Land separately.
3. Refactor one tool file end-to-end as a proof: switch to `Depends`, return a typed model, raise `ToolError`. Verify with `test_server.py` and a real client.
4. Once the pattern is proven, port the remaining tools file-by-file.
5. After all tools live under `app/mcp/`, delete `app/tools.py` and `app/prompts.py` and the `register_tools` / `register_prompts` plumbing in `main.py`.
6. Add the lifespan-managed shared `httpx.AsyncClient` (item 7). This is independent of the structural move and easier to verify against a stable baseline.

Each step is independently shippable and reversible.
