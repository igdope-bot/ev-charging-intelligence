"""Dashboard HTML estático con Plotly. Sin servidor: genera reports/dashboard.html.

Extensible: cada gráfico es una función que devuelve una Figure — para migrar
a Streamlit/Dash basta reutilizarlas.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ev_charging import config
from ev_charging.analysis import ChargingAnalyzer

_TEMPLATE = "plotly_white"


def fig_occupancy_by_hour(analyzer: ChargingAnalyzer) -> go.Figure:
    """Curva de ocupación media por hora: semana vs fin de semana."""
    data = analyzer.occupancy_by_hour()
    fig = go.Figure()
    for col, name in [("weekday", "Lun–Vie"), ("weekend", "Sáb–Dom")]:
        if col in data.columns:
            fig.add_trace(
                go.Scatter(x=data.index, y=data[col], name=name, mode="lines+markers")
            )
    fig.update_layout(
        title="Ocupación media por hora del día",
        xaxis_title="Hora",
        yaxis_title="Tasa de ocupación",
        yaxis_tickformat=".0%",
        template=_TEMPLATE,
    )
    return fig


def fig_stations_map(stations: pd.DataFrame) -> go.Figure:
    """Mapa de estaciones coloreado por potencia máxima."""
    df = stations.dropna(subset=["latitude", "longitude"])
    fig = px.scatter_map(
        df,
        lat="latitude",
        lon="longitude",
        color="max_power_kw",
        size="n_connectors",
        hover_name="name",
        hover_data={"operator": True, "town": True},
        color_continuous_scale="Viridis",
        zoom=4,
        title="Estaciones de carga en Chile",
    )
    fig.update_layout(template=_TEMPLATE, map_style="open-street-map")
    return fig


def fig_operator_share(analyzer: ChargingAnalyzer) -> go.Figure:
    """Top operadores por número de estaciones."""
    share = analyzer.operator_share().head(10)
    fig = px.bar(
        x=share.values,
        y=share.index,
        orientation="h",
        title="Participación por operador (% estaciones)",
        labels={"x": "% de estaciones", "y": ""},
    )
    fig.update_layout(template=_TEMPLATE, yaxis={"categoryorder": "total ascending"})
    return fig


def fig_price_by_operator(analyzer: ChargingAnalyzer) -> go.Figure | None:
    """Precio medio CLP/kWh por operador. None si no hay precios parseables."""
    prices = analyzer.price_summary()
    if prices.empty:
        return None
    fig = px.bar(
        prices.reset_index(),
        x="operator",
        y="mean",
        error_y=prices["max"] - prices["mean"],
        title="Precio medio por operador (CLP/kWh)",
        labels={"mean": "CLP/kWh", "operator": ""},
    )
    fig.update_layout(template=_TEMPLATE)
    return fig


def build_dashboard(
    analyzer: ChargingAnalyzer, out_path: Path | None = None
) -> Path:
    """Genera el dashboard HTML completo. Devuelve la ruta del archivo."""
    out_path = out_path or (config.REPORTS_DIR / "dashboard.html")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    figures = [
        fig_stations_map(analyzer.stations),
        fig_occupancy_by_hour(analyzer),
        fig_operator_share(analyzer),
    ]
    price_fig = fig_price_by_operator(analyzer)
    if price_fig is not None:
        figures.append(price_fig)

    parts = [
        "<html><head><meta charset='utf-8'><title>EV Charging Intelligence</title></head><body>",
        "<h1 style='font-family:sans-serif'>EV Charging Intelligence — Chile</h1>",
        "<p style='font-family:sans-serif;color:#666'>Datos de estaciones: OpenChargeMap. "
        "Ocupación: simulada (ver README).</p>",
    ]
    for i, fig in enumerate(figures):
        parts.append(fig.to_html(full_html=False, include_plotlyjs="cdn" if i == 0 else False))
    parts.append("</body></html>")

    out_path.write_text("\n".join(parts), encoding="utf-8")
    return out_path
