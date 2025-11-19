"""Simple sensor-to-InfluxDB logger (photodiodes excluded)."""

import os
import time
from typing import Dict, Optional

import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS

from . import config
from .sensor_reader import SensorReader


class DataLogger:
    def __init__(self, interval_seconds: int = 10, measurement: str = "sensor_data"):
        self.interval_seconds = max(1, interval_seconds)
        self.measurement = measurement
        self.reader = SensorReader()
        self.client: Optional[influxdb_client.InfluxDBClient] = None
        self.write_api = None

    def _ensure_client(self):
        if self.client:
            return
        if not config.influx_config_ready():
            raise RuntimeError("InfluxDB configuration is missing.")
        self.client = influxdb_client.InfluxDBClient(
            url=config.INFLUXDB_URL,
            token=config.INFLUXDB_TOKEN,
            org=config.INFLUXDB_ORG,
        )
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)

    def _build_point(self, data: Dict[str, float]):
        point = influxdb_client.Point(self.measurement)
        for key in (
            "voltage",
            "current",
            "power",
            "temperature",
            "humidity",
            "latitude",
            "longitude",
        ):
            value = data.get(key)
            if value is not None:
                point.field(key, float(value))
        return point

    def run_once(self):
        readings = self.reader.read_all()
        if not readings:
            print("No readings available; skipping write.")
            return

        try:
            self._ensure_client()
        except Exception as exc:
            print(f"InfluxDB not ready: {exc}")
            return

        point = self._build_point(readings)
        try:
            self.write_api.write(
                bucket=config.INFLUXDB_BUCKET,
                org=config.INFLUXDB_ORG,
                record=point,
            )
            print(f"Wrote measurement {self.measurement}: {readings}")
        except Exception as exc:
            print(f"Failed to write to InfluxDB: {exc}")

    def run_forever(self):
        while True:
            self.run_once()
            time.sleep(self.interval_seconds)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


if __name__ == "__main__":
    interval = _env_int("LOG_INTERVAL", 10)
    measurement = os.getenv("MEASUREMENT_NAME", "sensor_data")
    logger = DataLogger(interval_seconds=interval, measurement=measurement)
    logger.run_forever()
