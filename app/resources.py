"""Widget resources and metadata for the YNAB MCP server."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Final, Iterable, List

import mcp.types as types
from fastmcp import FastMCP

MIME_HTML_SKYBRIDGE: Final[str] = "text/html+skybridge"

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


@dataclass(frozen=True)
class WidgetDefinition:
    """Declarative definition for a skybridge widget template."""

    identifier: str
    title: str
    template_uri: str
    invoking: str
    invoked: str
    html: str
    description: str
    response_text: str = "Rendered widget."


TRANSACTIONS_WIDGET_ID: Final[str] = "transactions_table_widget"
TRANSACTION_DETAIL_WIDGET_ID: Final[str] = "transaction_detail_widget"


TRANSACTION_DETAIL_WIDGET_TEMPLATE: Final[str] = (
    "<div style=\"font-family:system-ui,sans-serif;font-size:14px;\">"
    "<strong>Transaction Detail Widget</strong><br>"
    "This widget will display a single transaction's detailed breakdown when implemented."
    "</div>"
)


TRANSACTIONS_WIDGET: Final[WidgetDefinition] = WidgetDefinition(
    identifier=TRANSACTIONS_WIDGET_ID,
    title="Transactions list",
    template_uri="ui://widget/transactions-table.html",
    invoking="Building transactions table",
    invoked="Transactions table ready",
    html=TRANSACTIONS_WIDGET_TEMPLATE,
    description="Skybridge ListView template summarizing recent YNAB transactions.",
    response_text="Rendered transactions list widget!",
)


TRANSACTION_DETAIL_WIDGET: Final[WidgetDefinition] = WidgetDefinition(
    identifier=TRANSACTION_DETAIL_WIDGET_ID,
    title="Transaction detail",
    template_uri="ui://widget/transaction-detail.html",
    invoking="Preparing transaction detail",
    invoked="Transaction detail displayed",
    html=TRANSACTION_DETAIL_WIDGET_TEMPLATE,
    description="Placeholder detail view for an individual transaction.",
    response_text="Rendered transaction detail widget!",
)


_WIDGETS: Final[List[WidgetDefinition]] = [
    TRANSACTIONS_WIDGET,
    TRANSACTION_DETAIL_WIDGET,
]


_WIDGETS_BY_ID: Final[Dict[str, WidgetDefinition]] = {
    widget.identifier: widget for widget in _WIDGETS
}


_WIDGETS_BY_URI: Final[Dict[str, WidgetDefinition]] = {
    widget.template_uri: widget for widget in _WIDGETS
}


_ANNOTATIONS: Final[Dict[str, bool]] = {
    "destructiveHint": False,
    "openWorldHint": False,
    "readOnlyHint": True,
}


def _resource_description(widget: WidgetDefinition) -> str:
    return widget.description or f"{widget.title} widget markup"


def _tool_meta(widget: WidgetDefinition) -> Dict[str, object]:
    return {
        "openai/outputTemplate": widget.template_uri,
        "openai/toolInvocation/invoking": widget.invoking,
        "openai/toolInvocation/invoked": widget.invoked,
        "openai/widgetAccessible": True,
        "openai/resultCanProduceWidget": True,
        "annotations": _ANNOTATIONS,
    }


def _embedded_widget_resource(widget: WidgetDefinition) -> types.EmbeddedResource:
    return types.EmbeddedResource(
        type="resource",
        resource=types.TextResourceContents(
            uri=widget.template_uri,
            mimeType=MIME_HTML_SKYBRIDGE,
            text=widget.html,
            title=widget.title,
        ),
    )


def _require_widget(identifier: str) -> WidgetDefinition:
    try:
        return _WIDGETS_BY_ID[identifier]
    except KeyError as exc:  # pragma: no cover - defensive guard
        raise ValueError(f"Unknown widget identifier: {identifier}") from exc


def widget_meta_base(identifier: str) -> Dict[str, object]:
    """Return reusable OpenAI Apps meta for the given widget."""

    return dict(_tool_meta(_require_widget(identifier)))


def widget_embedded_resource(identifier: str) -> types.EmbeddedResource:
    """Return the embedded resource descriptor for a widget."""

    return _embedded_widget_resource(_require_widget(identifier))


def widget_embedded_resource_json(identifier: str) -> Dict[str, object]:
    """Serialized embedded resource for inclusion in tool metadata."""

    return widget_embedded_resource(identifier).model_dump(mode="json")


def iter_widget_definitions() -> Iterable[WidgetDefinition]:
    """Expose widget definitions to other modules without leaking internals."""

    return tuple(_WIDGETS)


def register_resources(mcp: FastMCP) -> None:
    """Register MCP resource handlers following the FastMCP helper pattern."""

    server = mcp._mcp_server

    @server.list_resources()
    async def _list_resources() -> List[types.Resource]:
        return [
            types.Resource(
                name=widget.identifier,
                title=widget.title,
                uri=widget.template_uri,
                description=_resource_description(widget),
                mimeType=MIME_HTML_SKYBRIDGE,
                _meta=_tool_meta(widget),
            )
            for widget in _WIDGETS
        ]

    @server.list_resource_templates()
    async def _list_resource_templates() -> List[types.ResourceTemplate]:
        return [
            types.ResourceTemplate(
                name=widget.identifier,
                title=widget.title,
                uriTemplate=widget.template_uri,
                description=_resource_description(widget),
                mimeType=MIME_HTML_SKYBRIDGE,
                _meta=_tool_meta(widget),
            )
            for widget in _WIDGETS
        ]

    async def _handle_read_resource(
        req: types.ReadResourceRequest,
    ) -> types.ServerResult:
        widget = _WIDGETS_BY_URI.get(str(req.params.uri))
        if widget is None:
            return types.ServerResult(
                types.ReadResourceResult(
                    contents=[],
                    _meta={"error": f"Unknown resource: {req.params.uri}"},
                )
            )

        contents = [
            types.TextResourceContents(
                uri=widget.template_uri,
                mimeType=MIME_HTML_SKYBRIDGE,
                text=widget.html,
                title=widget.title,
                _meta=_tool_meta(widget),
            )
        ]

        return types.ServerResult(types.ReadResourceResult(contents=contents))

    server.request_handlers[types.ReadResourceRequest] = _handle_read_resource
