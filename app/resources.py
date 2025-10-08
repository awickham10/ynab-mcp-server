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
        """Widget UI template for rendering transactions in a ListView."""
        return """
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