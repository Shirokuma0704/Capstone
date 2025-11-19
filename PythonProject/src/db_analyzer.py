import re
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
from . import config


class DBAnalyzer:
    def __init__(self):
        self.client = None
        self.query_api = None

    def _ensure_client(self):
        if not config.influx_config_ready():
            raise ValueError("InfluxDB configuration is missing (INFLUXDB_URL/TOKEN/ORG/BUCKET).")
        if not self.client:
            self.client = influxdb_client.InfluxDBClient(
                url=config.INFLUXDB_URL,
                token=config.INFLUXDB_TOKEN,
                org=config.INFLUXDB_ORG
            )
            self.query_api = self.client.query_api()

    @staticmethod
    def _normalize_period(period: str) -> str:
        """
        Ensure the period is Flux-friendly (e.g., '24h' -> '-24h').
        Accepts already-prefixed relative durations (e.g., '-7d').
        """
        if not period:
            return "-24h"
        period = str(period).strip()
        # If already relative or now()
        if period.startswith("-") or period.lower().startswith("now()"):
            return period
        # Accept values like "24h", "7d", "1w"
        if re.fullmatch(r"[0-9]+[smhdw]", period):
            return f"-{period}"
        return "-24h"

    def get_summary(self, period="-24h"):
        """
        Gathers a summary of the sensor data over a given period.
        :param period: The time period to query (e.g., "-1h", "-7d"). Defaults to "-24h".
        :return: A dictionary containing the summary of data.
        """
        normalized_period = self._normalize_period(period)
        query = f'''
        from(bucket: "{config.INFLUXDB_BUCKET}")
          |> range(start: {normalized_period})
          |> filter(fn: (r) => r["_measurement"] == "sensor_data")
          |> filter(fn: (r) => r["_field"] == "voltage" or r["_field"] == "current" or r["_field"] == "power" or r["_field"] == "temperature")
          |> mean()
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
          |> group()
          |> last()
        '''
        try:
            self._ensure_client()
            tables = self.query_api.query(query)
            if not tables or not tables[0].records:
                return {"error": "No data found for the given period.", "period": normalized_period}

            record = tables[0].records[0]
            summary = {
                "period": normalized_period,
                "average_voltage": record.get("voltage"),
                "average_current": record.get("current"),
                "average_power": record.get("power"),
                "average_temperature": record.get("temperature"),
            }
            return summary
        except Exception as e:
            print(f"Error querying InfluxDB: {e}")
            return {"error": str(e)}


if __name__ == '__main__':
    # Example usage:
    # Ensure you have the rpi-dashboard-local environment running.
    analyzer = DBAnalyzer()
    summary_data = analyzer.get_summary("-1h")
    print("--- DB Analysis Summary (last 1 hour) ---")
    print(summary_data)
    print("-----------------------------------------")
