"""Static widget resources for YNAB MCP server.

These resources expose HTML/JS templates that can be referenced via
`openai/outputTemplate` metadata on tools to render rich UI inside
OpenAI Apps (SkyBridge) compatible clients.
"""

from fastmcp import FastMCP


def register_resources(mcp: FastMCP) -> None:
    """Register all widget/resource templates with the MCP server."""

    # Transactions table widget template
    @mcp.resource(
        uri="ui://widget/transactions-table.html",
        name="transactions_table_widget",
        mime_type="text/html+skybridge",
    )
    async def transactions_table_widget() -> str:
        # Minimal vanilla JS table renderer; expects a tool response structure
        # with a `widget` key containing columns & rows.
        return (
            "<div id=\"ynab-transactions-root\" style=\"font-family: system-ui, sans-serif; font-size:13px;\"></div>"  # container
            "<style>"
            "#ynab-transactions-root table{border-collapse:collapse;width:100%;}"
            "#ynab-transactions-root th,#ynab-transactions-root td{border:1px solid #ddd;padding:4px 6px;text-align:left;}"
            "#ynab-transactions-root th{background:#f5f7fa;font-weight:600;font-size:12px;}"
            "#ynab-transactions-root tr:nth-child(even){background:#fafbfc;}"
            "#ynab-transactions-root tr:hover{background:#eef5ff;}"
            "#ynab-transactions-root .neg{color:#b20000;font-weight:600;}"
            "#ynab-transactions-root .pos{color:#036703;}"
            "</style>"
            "<script type=\"module\">"
            "(function(){"
            "const container=document.getElementById('ynab-transactions-root');"
            "if(!container){return;}"
            "// The host should inject the tool call JSON alongside this template."
            "// We scan for a script tag with type application/json+widget as a simple convention."
            "const jsonScript=[...document.querySelectorAll('script')].find(s=>s.type==='application/json+widget');"
            "if(!jsonScript){container.innerHTML='<em>No transaction data found.</em>';return;}"
            "let payload;try{payload=JSON.parse(jsonScript.textContent);}catch(e){container.innerHTML='<em>Invalid widget data</em>';return;}"
            "if(!payload?.columns||!payload?.rows){container.innerHTML='<em>No rows</em>';return;}"
            "const tbl=document.createElement('table');"
            "const thead=document.createElement('thead');const htr=document.createElement('tr');"
            "for(const col of payload.columns){const th=document.createElement('th');th.textContent=col.label||col.key;htr.appendChild(th);}"
            "thead.appendChild(htr);tbl.appendChild(thead);"
            "const tbody=document.createElement('tbody');"
            "for(const row of payload.rows){const tr=document.createElement('tr');"
            "for(const col of payload.columns){let val=row[col.key];if(val==null) val='';"
            "if(col.key==='amount_formatted'){const trimmed=val.trim();const isNeg=trimmed.startsWith('(')||trimmed.startsWith('-');tr.classList.add(isNeg?'neg':'pos');}"
            "const td=document.createElement('td');td.textContent=val;tr.appendChild(td);}tbody.appendChild(tr);}"
            "tbl.appendChild(tbody);container.innerHTML='';container.appendChild(tbl);"
            "})();"
            "</script>"
        )

    # Placeholder resource for future single transaction detail widget
    @mcp.resource(
        uri="ui://widget/transaction-detail.html",
        name="transaction_detail_widget",
        mime_type="text/html+skybridge",
    )
    async def transaction_detail_widget() -> str:
        return (
            "<div style=\"font-family:system-ui,sans-serif;font-size:14px;\">"
            "<strong>Transaction Detail Widget</strong><br>"
            "This widget will display a single transaction's detailed breakdown when implemented."
            "</div>"
        )