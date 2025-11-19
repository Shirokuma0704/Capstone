import os
from dotenv import load_dotenv

# Load environment variables from a .env file if present
load_dotenv()

# InfluxDB configuration (defaults align with docker-compose dev stack)
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "my-super-secret-token")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "my-org")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "my-bucket")

# Gemini API Key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def influx_config_ready() -> bool:
    """Return True if all Influx settings are available."""
    return all([INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET])


def gemini_config_ready() -> bool:
    """Return True if Gemini can be initialized."""
    return bool(GEMINI_API_KEY)
