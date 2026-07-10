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


def kpi_header(stations: pd.DataFrame) -> str:
    """Fila de KPIs en HTML — todos calculados de datos reales."""
    operational = stations["is_operational"].astype("boolean").fillna(True)
    kpis = [
        (f"{len(stations):,}", "estaciones"),
        (f"{int(stations['n_connectors'].sum()):,}", "conectores"),
        (f"{stations['max_power_kw'].mean():.0f} kW", "potencia media"),
        (f"{operational.mean():.0%}", "operativas"),
        (f"{stations['town'].nunique()}", "comunas"),
        (f"{stations['operator'].nunique()}", "operadores"),
    ]
    cards = "".join(
        f"<div style='flex:1;min-width:110px;background:#f6f8fa;border-radius:8px;"
        f"padding:14px;text-align:center'>"
        f"<div style='font-size:26px;font-weight:700'>{value}</div>"
        f"<div style='color:#666;font-size:13px'>{label}</div></div>"
        for value, label in kpis
    )
    return f"<div style='display:flex;gap:10px;flex-wrap:wrap;font-family:sans-serif'>{cards}</div>"


def fig_network_growth(stations: pd.DataFrame) -> go.Figure:
    """Crecimiento acumulado de la red según fecha de registro en OCM (dato real)."""
    df = stations.dropna(subset=["date_created"]).sort_values("date_created")
    cumulative = pd.Series(range(1, len(df) + 1), index=df["date_created"])
    fig = go.Figure(go.Scatter(x=cumulative.index, y=cumulative.values,
                               mode="lines", fill="tozeroy"))
    fig.update_layout(
        title="Crecimiento de la red de carga en Chile (registro en OCM)",
        xaxis_title="", yaxis_title="Estaciones acumuladas", template=_TEMPLATE,
    )
    return fig


def fig_top_towns(stations: pd.DataFrame, top_n: int = 10) -> go.Figure:
    """Comunas con más estaciones."""
    top = stations["town"].dropna().value_counts().head(top_n)
    fig = px.bar(x=top.values, y=top.index, orientation="h",
                 title=f"Top {top_n} comunas por número de estaciones",
                 labels={"x": "estaciones", "y": ""})
    fig.update_layout(template=_TEMPLATE, yaxis={"categoryorder": "total ascending"})
    return fig


def fig_history_size(history_sizes: pd.DataFrame) -> go.Figure:
    """Tamaño de la red observado en los snapshots del cron (dato real acumulado)."""
    fig = go.Figure(go.Scatter(x=history_sizes.index, y=history_sizes["n_stations"],
                               mode="lines+markers"))
    fig.update_layout(
        title="Estaciones observadas por snapshot (recolección automática cada 6h)",
        xaxis_title="", yaxis_title="Estaciones", template=_TEMPLATE,
    )
    return fig


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
        title="Ocupación media por hora del día (simulación — ver README)",
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
    analyzer: ChargingAnalyzer,
    out_path: Path | None = None,
    history_sizes: pd.DataFrame | None = None,
) -> Path:
    """Genera el dashboard HTML completo. Devuelve la ruta del archivo.

    Args:
        history_sizes: salida de history.network_size_over_time(); si tiene
            2+ snapshots se agrega la sección de histórico observado.
    """
    out_path = out_path or (config.REPORTS_DIR / "dashboard.html")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    figures = [
        fig_stations_map(analyzer.stations),
        fig_network_growth(analyzer.stations),
        fig_top_towns(analyzer.stations),
        fig_operator_share(analyzer),
    ]
    price_fig = fig_price_by_operator(analyzer)
    if price_fig is not None:
        figures.append(price_fig)
    if history_sizes is not None and len(history_sizes) >= 2:
        figures.append(fig_history_size(history_sizes))
    if analyzer.occupancy is not None:
        figures.append(fig_occupancy_by_hour(analyzer))

    parts = [
        "<html><head><meta charset='utf-8'><title>EV Charging Intelligence</title>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'></head>"
        "<body style='max-width:1100px;margin:0 auto;padding:0 12px'>",
        "<h1 style='font-family:sans-serif'>EV Charging Intelligence — Chile</h1>",
        "<p style='font-family:sans-serif;color:#666'>Datos: OpenChargeMap, "
        "actualizados automáticamente cada 6 horas. La curva de ocupación es "
        "simulada (ver README); el resto son datos reales.</p>",
        kpi_header(analyzer.stations),
    ]
    for i, fig in enumerate(figures):
        parts.append(fig.to_html(full_html=False, include_plotlyjs="cdn" if i == 0 else False))
    parts.append(
        "<p style='font-family:sans-serif;color:#999;font-size:12px'>"
        "Generado automáticamente — "
        "<a href='https://github.com/igdope-bot/ev-charging-intelligence'>código en GitHub</a></p>"
        "</body></html>"
    )

    out_path.write_text("\n".join(parts), encoding="utf-8")
    return out_path
