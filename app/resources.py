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
        """Widget UI template for rendering the transactions summary card."""
        return """
<Card size="md">
    <Col gap={3}>
        <Row align="start">
            <Col gap={0}>
                <Title value={summary.title} size="sm" />
                <Caption value={summary.subtitle} size="sm" color="secondary" />
            </Col>
            <Spacer />
            <Badge label={`${summary.displayCount} of ${summary.rowCount}`} size="sm" variant="soft" />
        </Row>
        <Row gap={3}>
            <Col gap={0}>
                <Caption value="Outflow" size="sm" color="secondary" />
                <Text value={summary.outflow} size="sm" weight="semibold" color="danger" />
            </Col>
            <Col gap={0}>
                <Caption value="Inflow" size="sm" color="secondary" />
                <Text value={summary.inflow} size="sm" weight="semibold" color="success" />
            </Col>
            <Col gap={0}>
                <Caption value="Net" size="sm" color="secondary" />
                <Text value={summary.net} size="sm" weight="semibold" color={summary.netColor} />
            </Col>
        </Row>
        <Divider />
        <Col gap={2}>
            {rows.map((item) => (
                <Row key={item.id} align="start" gap={3}>
                    <Col gap={1}>
                        <Badge label={item.date} size="sm" variant="soft" />
                        {item.needsApproval && (
                            <Badge label="Needs approval" size="sm" color="warning" variant="soft" />
                        )}
                    </Col>
                    <Col flex="auto" gap={0}>
                        <Text value={item.payee} size="sm" weight="semibold" maxLines={1} />
                        <Caption value={item.category} size="sm" color="secondary" maxLines={1} />
                        {item.memo && (
                            <Caption value={item.memo} size="sm" color="tertiary" maxLines={1} />
                        )}
                    </Col>
                    <Spacer />
                    <Col align="end" gap={0}>
                        <Text value={item.amount} size="sm" weight="semibold" color={item.amountColor} />
                    </Col>
                </Row>
            ))}
            {rows.length === 0 && (
                <Row align="center" justify="center" padding={{ y: 4 }}>
                    <Text value="No transactions to show yet." size="sm" color="secondary" />
                </Row>
            )}
        </Col>
    </Col>
</Card>
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