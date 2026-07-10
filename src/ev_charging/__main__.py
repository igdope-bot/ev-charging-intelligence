"""Pipeline completo: descarga → simula ocupación → analiza → dashboard.

Uso: python -m ev_charging [--max-results 300] [--operator enel]
"""

import argparse
import logging

from ev_charging import config
from ev_charging.analysis import ChargingAnalyzer
from ev_charging.api_client import OpenChargeMapClient
from ev_charging.availability import generate_occupancy
from ev_charging.dashboard import build_dashboard
from ev_charging.history import load_snapshots, network_size_over_time

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("ev_charging.pipeline")


def main() -> None:
    parser = argparse.ArgumentParser(description="EV Charging Intelligence pipeline")
    parser.add_argument("--max-results", type=int, default=config.DEFAULT_MAX_RESULTS)
    parser.add_argument("--operator", type=str, default=None, help="ej: enel")
    parser.add_argument("--days", type=int, default=14, help="días de ocupación simulada")
    args = parser.parse_args()

    config.ensure_dirs()

    client = OpenChargeMapClient()
    stations = client.fetch_stations(max_results=args.max_results, operator_name=args.operator)
    client.save_snapshot(stations)

    stations_df = client.to_dataframe(stations)
    occupancy_df = generate_occupancy(stations_df, days=args.days)
    occupancy_df.to_parquet(config.PROCESSED_DATA_DIR / "occupancy.parquet", index=False)

    history_sizes = network_size_over_time(load_snapshots())

    analyzer = ChargingAnalyzer(stations_df, occupancy_df)
    path = build_dashboard(analyzer, history_sizes=history_sizes)
    logger.info("Dashboard generado: %s", path)
    logger.info("Horas peak:\n%s", analyzer.peak_hours())


if __name__ == "__main__":
    main()
