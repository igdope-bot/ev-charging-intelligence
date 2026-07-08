"""Tests del cliente OCM — 100% offline con requests mockeado."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from ev_charging.api_client import OpenChargeMapClient, OpenChargeMapError


def make_client() -> OpenChargeMapClient:
    return OpenChargeMapClient(api_key="test-key", max_retries=2)


def test_missing_api_key_raises():
    with patch("ev_charging.config.OCM_API_KEY", ""):
        with pytest.raises(OpenChargeMapError, match="OCM_API_KEY"):
            OpenChargeMapClient(api_key="")


def test_parse_station_full(sample_poi):
    parsed = OpenChargeMapClient._parse_station(sample_poi)
    assert parsed["station_id"] == 12345
    assert parsed["operator"] == "Enel X"
    assert parsed["n_connectors"] == 2
    assert parsed["max_power_kw"] == 50
    assert parsed["is_operational"] is True


def test_parse_station_tolerates_missing_fields():
    parsed = OpenChargeMapClient._parse_station({"ID": 1})
    assert parsed["station_id"] == 1
    assert parsed["operator"] is None
    assert parsed["n_connectors"] == 0
    assert parsed["max_power_kw"] == 0


def test_fetch_stations_filters_by_operator(sample_poi):
    client = make_client()
    other = dict(sample_poi, ID=2, OperatorInfo={"Title": "Copec Voltex"})
    with patch.object(client, "_get", return_value=[sample_poi, other]):
        result = client.fetch_stations(operator_name="enel")
    assert len(result) == 1
    assert result[0]["operator"] == "Enel X"


def test_fetch_stations_unexpected_response_raises():
    client = make_client()
    with patch.object(client, "_get", return_value={"error": "nope"}):
        with pytest.raises(OpenChargeMapError, match="inesperada"):
            client.fetch_stations()


def test_get_retries_on_connection_error_then_fails():
    client = make_client()
    with patch.object(client.session, "get", side_effect=requests.ConnectionError("boom")):
        with patch("time.sleep"):  # no esperar de verdad
            with pytest.raises(OpenChargeMapError, match="2 intentos"):
                client._get("poi", {})


def test_get_no_retry_on_4xx():
    client = make_client()
    resp = MagicMock(status_code=404)
    resp.raise_for_status.side_effect = requests.HTTPError(response=resp)
    with patch.object(client.session, "get", return_value=resp) as mock_get:
        with pytest.raises(OpenChargeMapError, match="HTTP 404"):
            client._get("poi", {})
    assert mock_get.call_count == 1  # sin reintentos


def test_to_dataframe(sample_poi):
    stations = [OpenChargeMapClient._parse_station(sample_poi)]
    df = OpenChargeMapClient.to_dataframe(stations)
    assert len(df) == 1
    assert str(df["date_created"].dtype).startswith("datetime64")


def test_save_snapshot(tmp_path, sample_poi):
    client = make_client()
    stations = [OpenChargeMapClient._parse_station(sample_poi)]
    path = client.save_snapshot(stations, out_dir=tmp_path)
    assert path.exists()
    assert path.suffix == ".json"
