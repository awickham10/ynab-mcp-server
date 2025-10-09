"""Static widget resources for YNAB MCP server."""

from typing import Final

import mcp.types as types
from fastmcp import FastMCP

MIME_HTML_SKYBRIDGE: Final[str] = "text/html+skybridge"
TRANSACTIONS_WIDGET_URI: Final[str] = "ui://widget/transactions-table.html"
TRANSACTIONS_WIDGET_TITLE: Final[str] = "Transactions list"

TRANSACTIONS_WIDGET_TEMPLATE: Final[str] = """
<ListView>
    {rows.map((t) => (
        <ListViewItem
            key={t.id}
            gap={2}
            onClickAction={{ type: "transaction.select", payload: { id: t.id } }}
        >
            <Col flex={1} gap={1}>
                <Row>
                    <Text value={t.payee} size="sm" weight="semibold" maxLines={1} />
                    <Spacer />
                    <Text value={t.amount} weight="semibold" color={t.amountColor} />
                </Row>
                <Row>
                    <Caption value={`${t.date} • ${t.category}`} color="secondary" maxLines={1} />
                    <Spacer />
                    {t.needsApproval && (
                        <Badge label="Needs approval" color="warning" variant="soft" />
                    )}
                </Row>
                {t.memo && (
                    <Text value={t.memo} size="sm" color="tertiary" maxLines={1} />
                )}
            </Col>
        </ListViewItem>
    ))}
</ListView>
"""

TRANSACTIONS_WIDGET_EMBEDDED_RESOURCE: Final[types.EmbeddedResource] = (
    types.EmbeddedResource(
        type="resource",
        resource=types.TextResourceContents(
            uri=TRANSACTIONS_WIDGET_URI,
            mimeType=MIME_HTML_SKYBRIDGE,
            text=TRANSACTIONS_WIDGET_TEMPLATE,
            title=TRANSACTIONS_WIDGET_TITLE,
        ),
    )
)

TRANSACTIONS_WIDGET_EMBEDDED_RESOURCE_JSON: Final[dict] = (
    TRANSACTIONS_WIDGET_EMBEDDED_RESOURCE.model_dump(mode="json")
)

TRANSACTIONS_WIDGET_META_BASE: Final[dict] = {
    "openai/outputTemplate": TRANSACTIONS_WIDGET_URI,
    "openai/toolInvocation/invoking": "Building transactions table",
    "openai/toolInvocation/invoked": "Transactions table ready",
    "openai/widgetAccessible": True,
    "openai/resultCanProduceWidget": True,
}


def register_resources(mcp: FastMCP) -> None:
    """Register all widget/resource templates with the MCP server."""

    @mcp.resource(
        uri=TRANSACTIONS_WIDGET_URI,
        name="transactions_table_widget",
        mime_type=MIME_HTML_SKYBRIDGE,
    )
    async def transactions_table_widget() -> str:
        """Widget UI template for rendering transactions in a ListView."""
        return TRANSACTIONS_WIDGET_TEMPLATE

    # Placeholder resource for future single transaction detail widget
    @mcp.resource(
        uri="ui://widget/transaction-detail.html",
        name="transaction_detail_widget",
        mime_type=MIME_HTML_SKYBRIDGE,
    )
    async def transaction_detail_widget() -> str:
        return (
            "<div style=\"font-family:system-ui,sans-serif;font-size:14px;\">"
            "<strong>Transaction Detail Widget</strong><br>"
            "This widget will display a single transaction's detailed breakdown when implemented."
            "</div>"
        )