"""Fixtures compartidos. Todos los tests corren offline (API mockeada)."""

import pandas as pd
import pytest

SAMPLE_POI = {
    "ID": 12345,
    "UsageCost": "$250/kWh",
    "AddressInfo": {
        "Title": "Enel X Parque Arauco",
        "Latitude": -33.4025,
        "Longitude": -70.5773,
        "Town": "Las Condes",
        "StateOrProvince": "Región Metropolitana",
    },
    "OperatorInfo": {"Title": "Enel X"},
    "Connections": [{"PowerKW": 50}, {"PowerKW": 22}],
    "StatusType": {"IsOperational": True},
    "DateCreated": "2023-05-10T12:00:00Z",
}


@pytest.fixture
def sample_poi() -> dict:
    return dict(SAMPLE_POI)


@pytest.fixture
def stations_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "station_id": 1,
                "name": "Enel X Parque Arauco",
                "operator": "Enel X",
                "usage_cost": "$250/kWh",
                "latitude": -33.40,
                "longitude": -70.58,
                "town": "Las Condes",
                "state": "RM",
                "n_connectors": 4,
                "max_power_kw": 50,
                "is_operational": True,
                "date_created": pd.Timestamp("2023-05-10"),
            },
            {
                "station_id": 2,
                "name": "Copec Voltex Ruta 5",
                "operator": "Copec Voltex",
                "usage_cost": "290 CLP/kWh",
                "latitude": -36.82,
                "longitude": -73.05,
                "town": "Concepción",
                "state": "Biobío",
                "n_connectors": 2,
                "max_power_kw": 150,
                "is_operational": True,
                "date_created": pd.Timestamp("2024-01-15"),
            },
        ]
    )
