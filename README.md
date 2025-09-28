# YNAB MCP Server

This is a Model Context Protocol (MCP) server that provides secure access to your YNAB (You Need A Budget) data through OAuth authentication.

## Features

- **Secure OAuth Authentication**: Uses YNAB's OAuth2 flow to authenticate users
- **Read-only Access**: Configured to r**Key OAuth Endpoints:**
- **Discovery**: `http://localhost:8000/.well-known/oauth-protected-resource` 
- **Authorization**: `http://localhost:8000/authorize`
- **Token Exchange**: `http://localhost:8000/token` 
- **OAuth Callback**: `http://localhost:8000/oauth/callback`
- **MCP Endpoint**: `http://localhost:8000/mcp` (requires authenticated token)t only read permissions by default
- **Comprehensive API Coverage**: Provides tools to access budgets, accounts, transactions, and categories
- **MCP Integration**: Works with any MCP-compatible client (Claude Desktop, etc.)

## Setup

### 1. Create a YNAB OAuth Application

1. Go to [YNAB Developer Settings](https://app.ynab.com/settings/developer)
2. Click "New Application" under OAuth Applications
3. Fill in your application details:
   - **Application Name**: Your app name (e.g., "My YNAB MCP Server")
   - **Website URL**: Your website or GitHub repo
   - **Redirect URI**: `http://localhost:8000/oauth/callback`
4. Save the application and note your **Client ID** and **Client Secret**

**Important**: The redirect URI must be exactly `http://localhost:8000/oauth/callback` (note the `/oauth/callback` path, not `/auth/callback`).

### 2. Configure the Server

Create a `.env` file in the root directory with your YNAB OAuth credentials:

```bash
# Copy the template
cp .env.template .env

# Edit the .env file with your YNAB OAuth app credentials
YNAB_CLIENT_ID=your-actual-ynab-client-id
YNAB_CLIENT_SECRET=your-actual-ynab-client-secret  
YNAB_BASE_URL=http://localhost:8000
YNAB_READ_ONLY=true
```

**Important**: The `YNAB_BASE_URL` must exactly match the "Redirect URI" configured in your YNAB OAuth application. The OAuth callback will be at `{YNAB_BASE_URL}/oauth/callback`.

### 3. Install Dependencies

```bash
# Install uv if you haven't already
pip install uv

# Install dependencies
uv install
```

### 4. Run the Server

```bash
# Run the server in HTTP mode
uv run fastmcp run ./server.py:mcp --transport http --port 8000

# Or for development with auto-reload and MCP Inspector
uv run fastmcp dev ./server.py:mcp --transport http --port 8000
```

**Note**: We use `./server.py:mcp` instead of `app.main:mcp` due to FastMCP module resolution. The `server.py` file is a simple wrapper that imports the main application.

The server will start in HTTP mode and be available at `http://localhost:8000`. For development with the MCP Inspector, the dev command will also start a web interface for testing tools and prompts.

## Available Tools

The server provides the following MCP tools with comprehensive error handling:

### `get_budgets`
Get all budgets for the authenticated user.

**Parameters:**
- `access_token`: YNAB access token (automatically provided after OAuth)
- `include_accounts`: Whether to include account summaries (optional)

### `get_budget`
Get detailed information for a specific budget.

**Parameters:**
- `access_token`: YNAB access token
- `budget_id`: The budget ID (use 'last-used' for most recent)

### `get_accounts`
Get all accounts for a specific budget.

**Parameters:**
- `access_token`: YNAB access token
- `budget_id`: The budget ID (use 'last-used' for most recent)

### `get_account`
Get information for a specific account.

**Parameters:**
- `access_token`: YNAB access token
- `budget_id`: The budget ID
- `account_id`: The account ID

### `get_transactions`
Get transactions for a specific budget with smart compound filtering that automatically chooses the most efficient API endpoint to minimize data transfer.

**Smart Filtering Strategy:**
1. **Account + any other filters** → Uses account endpoint, filters rest in-memory
2. **Category + Payee** → Uses category endpoint, filters payee in-memory  
3. **Category only** → Uses category endpoint
4. **Payee only** → Uses payee endpoint
5. **No filters** → Uses general transactions endpoint

**Parameters:**
- `budget_id`: The budget ID (use 'last-used' for most recent)
- `account_id`: Optional account ID to filter transactions for a specific account
- `payee_id`: Optional payee ID to filter transactions for a specific payee
- `category_id`: Optional category ID to filter transactions for a specific category
- `since_date`: Optional date filter (format: YYYY-MM-DD)
- `transaction_type`: Optional transaction type filter ('uncategorized' or 'unapproved')

**Compound Filtering Examples:**
```python
# Account + Category: Uses account endpoint, filters by category in-memory
get_transactions(account_id="checking-123", category_id="groceries-456")

# Category + Payee: Uses category endpoint, filters by payee in-memory  
get_transactions(category_id="groceries-456", payee_id="walmart-789")

# Account + Category + Payee: Uses account endpoint, filters both in-memory
get_transactions(account_id="checking-123", category_id="groceries-456", payee_id="walmart-789")
```

### `get_categories`
Get all categories for a specific budget.

**Parameters:**
- `access_token`: YNAB access token
- `budget_id`: The budget ID (use 'last-used' for most recent)

### `get_payees`
Get all payees for a specific budget.

**Parameters:**
- `access_token`: YNAB access token
- `budget_id`: The budget ID (use 'last-used' for most recent)

### `analyze_spending`
Analyze spending patterns with automated insights.

**Parameters:**
- `budget_id`: The budget ID (use 'last-used' for most recent)
- `months`: Number of months to analyze (default: 3)

### `update_transaction`
Update an existing transaction, including the memo field.

**Parameters:**
- `budget_id`: The budget ID
- `transaction_id`: The transaction ID to update
- `memo`: Transaction memo (max 500 characters, optional)
- `amount`: Amount in standard currency format (e.g., 50.00 for $50.00, optional)
- `payee_id`: Payee ID (optional)
- `payee_name`: Payee name - alternative to payee_id (optional)
- `category_id`: Category ID (optional)
- `cleared`: Cleared status ('cleared', 'uncleared', 'reconciled', optional)
- `approved`: Whether transaction is approved (boolean, optional)
- `flag_color`: Flag color ('red', 'orange', 'yellow', 'green', 'blue', 'purple', optional)
- `date`: Transaction date in YYYY-MM-DD format (optional)

**Example Usage:**
```python
# Update only the memo field
await update_transaction(
    budget_id="last-used",
    transaction_id="abc-123",
    memo="Updated memo for this transaction"
)

# Update multiple fields
await update_transaction(
    budget_id="last-used", 
    transaction_id="abc-123",
    memo="Grocery shopping at Whole Foods",
    amount=87.45,
    cleared="cleared",
    flag_color="green"
)
```

## Available Prompts

### `budget_summary`
Generate a prompt for comprehensive budget analysis.

**Parameters:**
- `budget_id`: The budget ID to analyze (defaults to 'last-used')

### `spending_analysis`
Generate a prompt for detailed spending pattern analysis.

**Parameters:**
- `budget_id`: The budget ID to analyze (defaults to 'last-used')
- `category_name`: Specific category to focus on (optional)
- `months`: Number of months to analyze (default: 3)

### `budget_setup`
Generate a prompt for budget setup and optimization guidance.

**Parameters:**
- `budget_id`: The budget ID to analyze (defaults to 'last-used')

### `debt_analysis`
Generate a prompt for debt analysis and payoff strategy.

**Parameters:**
- `budget_id`: The budget ID to analyze (defaults to 'last-used')

## Authentication Flow

1. When a client first connects, they'll be redirected to YNAB's OAuth authorization page
2. User logs into YNAB and approves the application
3. User is redirected back with an authorization code
4. The server exchanges the code for an access token
5. The access token is used to make authenticated API calls to YNAB

## Configuration Options

The `YNABProvider` supports several configuration options:

```python
auth_provider = YNABProvider(
    client_id="your-client-id",
    client_secret="your-client-secret", 
    base_url="http://localhost:8000",
    read_only=True,                     # Request read-only scope
    redirect_path="/auth/callback",     # Custom callback path
    allowed_client_redirect_uris=[      # Restrict client redirects
        "http://localhost:*",
        "https://your-domain.com/*"
    ]
)
```

## Environment Variables

You can also configure the provider using environment variables in your `.env` file:

```bash
YNAB_CLIENT_ID=your-client-id
YNAB_CLIENT_SECRET=your-client-secret
YNAB_BASE_URL=http://localhost:8000
YNAB_READ_ONLY=true
YNAB_REDIRECT_PATH=/auth/callback
```

## Data Format

YNAB uses "milliunits" for currency amounts. This means:
- $123.45 is represented as 123450 milliunits
- €4.92 is represented as 4920 milliunits

**The MCP server returns both formats:**
- Raw milliunits (e.g., `amount: 123450`) - for precise calculations
- Formatted amounts (e.g., `amount_formatted: 123.45`) - for human readability

All dates are in ISO format (YYYY-MM-DD) and use UTC timezone.

## Rate Limiting

YNAB API has a rate limit of 200 requests per hour per access token. The tools will handle rate limiting errors appropriately.

## Development

### Running in Development Mode

```bash
# Run with auto-reload and MCP Inspector
uv run fastmcp dev ./server.py:mcp --transport http --port 8000

# The development server provides:
# - Auto-reload when files change
# - MCP Inspector web interface (usually at http://localhost:3000)
# - Enhanced debugging output
# - HTTP endpoints accessible at http://localhost:8000
```

### Project Structure

The server follows an enterprise architecture pattern:

```
app/
├── __init__.py              # Package initialization
├── main.py                  # Main server factory and configuration
├── auth/
│   └── ynab.py             # Custom YNAB OAuth provider
├── config/
│   └── __init__.py         # Environment-based configuration
├── exceptions/
│   └── __init__.py         # Custom exception hierarchy
├── models/
│   └── __init__.py         # Pydantic data models
├── prompts/
│   └── __init__.py         # MCP prompts for analysis
├── services/
│   └── __init__.py         # Business logic layer
└── tools/
    └── __init__.py         # MCP tools implementation
server.py                   # FastMCP runner script
```

### Verification

To verify the server is working correctly:

```bash
# Check that all tools and prompts are registered
uv run python -c "
import asyncio
from app.main import mcp

async def test_server():
    tools = await mcp.get_tools()
    prompts = await mcp.get_prompts()
    print(f'✅ Tools available: {len(tools)}')
    print(f'💬 Prompts available: {len(prompts)}')
    print('🔧 Tools:', ', '.join(sorted(tools.keys())))
    print('💭 Prompts:', ', '.join(sorted(prompts.keys())))

asyncio.run(test_server())
"
```

### MCP Inspector

When running in development mode (`uv run fastmcp dev ./server.py:mcp --transport http --port 8000`), FastMCP automatically starts the MCP Inspector - a web-based tool for testing your MCP server:

- **Purpose**: Interactive testing interface for MCP tools and prompts
- **Access**: Usually available at `http://localhost:3000` (check console output)
- **Features**: 
  - Test individual tools with custom parameters
  - View tool schemas and documentation
  - Test prompts and see generated responses
  - Monitor server logs and debug information

This is especially useful for testing your YNAB OAuth flow and verifying that all tools work correctly before connecting to a full MCP client.

### Testing the OAuth Flow

1. Start the development server: `uv run fastmcp dev ./server.py:mcp --transport http --port 8000`
2. The server will be available at `http://localhost:8000`
3. **OAuth Discovery**: Navigate to `http://localhost:8000/.well-known/oauth-protected-resource` to see OAuth metadata
4. **Manual OAuth Test**: Navigate to `http://localhost:8000/auth/authorize` to test the OAuth flow directly
5. You'll be redirected to YNAB for authentication
6. After approval, you'll be redirected back with an authorization code
7. The server will exchange the code for an access token
8. You can now test the MCP tools through the MCP Inspector or connect with MCP clients

**Key OAuth Endpoints:**
- **Discovery**: `http://localhost:8000/.well-known/oauth-protected-resource` 
- **Authorization**: `http://localhost:8000/auth/authorize`
- **Token Exchange**: `http://localhost:8000/auth/token` 
- **MCP Endpoint**: `http://localhost:8000/mcp` (requires authenticated token)

### Adding New Tools

To add new YNAB API endpoints, edit the files in the `app/tools/` directory:

1. Add a new tool function in `app/tools/__init__.py`
2. Use the `@mcp.tool` decorator
3. Import and use the `YNABService` for API calls
4. Handle errors using custom exceptions from `app.exceptions`
5. Register the tool in the `register_tools()` function

Example:
```python
@mcp.tool
async def get_payee_transactions(
    budget_id: str = "last-used", 
    payee_id: str = "",
    access_token: str = ""
) -> dict:
    """Get all transactions for a specific payee"""
    if not payee_id:
        raise ValueError("Payee ID is required")
    
    try:
        service = YNABService(access_token)
        transactions = await service.get_transactions(budget_id)
        
        # Filter transactions by payee
        payee_transactions = [
            t for t in transactions 
            if t.get('payee_id') == payee_id
        ]
        
        return {
            "transactions": payee_transactions,
            "total_count": len(payee_transactions)
        }
    except Exception as e:
        logger.error(f"Error fetching payee transactions: {e}")
        raise YNABServiceError(f"Failed to get payee transactions: {e}")
```

## Troubleshooting

### Common Issues

1. **"Client ID is required" error**: Make sure you've updated the client ID in the code
2. **"Redirect URI mismatch"**: Ensure the redirect URI in YNAB app settings matches your `base_url + /auth/callback`
3. **"Token expired"**: YNAB tokens expire after 2 hours; the OAuth flow will need to be repeated

### Debug Mode

Enable debug logging by setting the log level:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## License

This project is provided as-is for educational and personal use. Please ensure compliance with YNAB's API Terms of Service.

## Contributing

Feel free to submit issues and pull requests to improve the server functionality.
