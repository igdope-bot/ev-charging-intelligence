"""Tests de análisis y simulador de ocupación."""

import pandas as pd
import pytest

from ev_charging.analysis import ChargingAnalyzer
from ev_charging.availability import generate_occupancy


@pytest.fixture
def occupancy_df(stations_df) -> pd.DataFrame:
    return generate_occupancy(stations_df, days=3)


# --- availability -----------------------------------------------------------

def test_generate_occupancy_shape(stations_df, occupancy_df):
    assert len(occupancy_df) == len(stations_df) * 3 * 24
    assert set(occupancy_df.columns) == {
        "station_id", "timestamp", "occupied", "capacity", "occupancy_rate"
    }


def test_occupancy_rate_bounds(occupancy_df):
    assert occupancy_df["occupancy_rate"].between(0, 1).all()
    assert (occupancy_df["occupied"] <= occupancy_df["capacity"]).all()


def test_generate_occupancy_reproducible(stations_df):
    a = generate_occupancy(stations_df, days=2, seed=7)
    b = generate_occupancy(stations_df, days=2, seed=7)
    pd.testing.assert_frame_equal(a, b)


def test_generate_occupancy_missing_columns_raises():
    with pytest.raises(ValueError, match="Faltan columnas"):
        generate_occupancy(pd.DataFrame({"station_id": [1]}))


# --- analysis ----------------------------------------------------------------

def test_stations_by_region(stations_df):
    result = ChargingAnalyzer(stations_df).stations_by_region()
    assert result.loc["RM", "n_stations"] == 1
    assert result.loc["Biobío", "total_connectors"] == 2


def test_operator_share_sums_100(stations_df):
    share = ChargingAnalyzer(stations_df).operator_share()
    assert share.sum() == pytest.approx(100, abs=0.5)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("$250/kWh", 250.0),
        ("290 CLP/kWh", 290.0),
        ("$1.250/kWh", 1250.0),   # separador de miles chileno
        ("Gratis", None),
        (None, None),
        ("$999999/kWh", None),    # fuera de rango razonable
    ],
)
def test_parse_price_clp_kwh(text, expected):
    assert ChargingAnalyzer.parse_price_clp_kwh(text) == expected


def test_price_summary(stations_df):
    result = ChargingAnalyzer(stations_df).price_summary()
    assert len(result) == 2
    assert result.loc["Enel X", "mean"] == 250


def test_occupancy_by_hour_has_24_rows(stations_df, occupancy_df):
    result = ChargingAnalyzer(stations_df, occupancy_df).occupancy_by_hour()
    assert len(result) == 24


def test_peak_hours_in_expected_range(stations_df, occupancy_df):
    peaks = ChargingAnalyzer(stations_df, occupancy_df).peak_hours(top_n=3)
    # el simulador modela peaks 8-10 y 18-21
    assert all(h in range(7, 22) for h in peaks.index)


def test_occupancy_methods_require_data(stations_df):
    analyzer = ChargingAnalyzer(stations_df)
    with pytest.raises(ValueError, match="ocupación"):
        analyzer.occupancy_by_hour()
