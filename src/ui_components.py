from __future__ import annotations

from dash import dcc, html


def page_header(title: str, subtitle: str, eyebrow: str | None = None):
    return html.Div(
        [
            html.Div(eyebrow, className="page-section-eyebrow") if eyebrow else None,
            html.H3(title, className="page-section-title"),
            html.P(subtitle, className="page-section-subtitle"),
        ],
        className="page-section-header",
    )


def kpi_card(label: str, value: str, hint: str, accent: str = "teal"):
    return html.Div(
        [
            html.Div(className=f"kpi-accent kpi-accent--{accent}"),
            html.Div(label, className="kpi-label"),
            html.Div(value, className="kpi-value"),
            html.Div(hint, className="kpi-hint"),
        ],
        className="kpi-card",
    )


def chart_card(
    graph_id: str,
    title: str,
    subtitle: str,
    graph_height: str = "360px",
    graph_config: dict | None = None,
):
    merged_config = {"displayModeBar": False, "responsive": True}
    if graph_config:
        merged_config.update(graph_config)

    return html.Div(
        [
            html.Div(
                [
                    html.H4(title, className="chart-card-title"),
                    html.P(subtitle, className="chart-card-subtitle"),
                ],
                className="chart-card-head",
            ),
            dcc.Graph(
                id=graph_id,
                config=merged_config,
                className="chart-figure",
                style={"height": graph_height},
            ),
        ],
        className="chart-card",
    )


def warning_card(message: str, title: str = "تنبيه", tone: str = "warning"):
    return html.Div(
        [
            html.Div(title, className="message-title"),
            html.Div(message, className="message-text"),
        ],
        className=f"message-card message-card--{tone}",
    )


def metric_list_card(title: str, subtitle: str, rows: list[dict], empty_message: str = "لا توجد بيانات متاحة حالياً."):
    body = (
        html.Div(empty_message, className="metric-list-empty")
        if not rows
        else html.Div(
            [
                html.Div(
                    [
                        html.Div(row["label"], className="metric-row-label"),
                        html.Div(row["value"], className=f"metric-row-value metric-row-value--{row.get('tone', 'neutral')}"),
                    ],
                    className="metric-row",
                )
                for row in rows
            ],
            className="metric-list-body",
        )
    )

    return html.Div(
        [
            html.Div(
                [
                    html.H4(title, className="chart-card-title"),
                    html.P(subtitle, className="chart-card-subtitle"),
                ],
                className="chart-card-head",
            ),
            html.Div(body, className="metric-list-card"),
        ],
        className="chart-card chart-card--compact",
    )
