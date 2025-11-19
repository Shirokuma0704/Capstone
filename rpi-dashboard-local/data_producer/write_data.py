import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
import time
import os
import requests  # API 호출을 위한 라이브러리

# --- InfluxDB 연결 정보 ---
token = os.getenv('INFLUXDB_TOKEN', 'my-super-secret-token')
org = os.getenv('INFLUXDB_ORG', 'my-org')
bucket = os.getenv('INFLUXDB_BUCKET', 'my-bucket')
influx_url = os.getenv('INFLUXDB_URL', 'http://100.116.239.122:8086')

# --- 하드웨어 API 주소 (기본: 로컬 hardware_api) ---
hardware_api_url = os.getenv("HARDWARE_API_URL", "http://127.0.0.1:5000")
sensor_api_url = f"{hardware_api_url}/api/v1/sensors"

# --- InfluxDB 클라이언트 초기화 ---
client = influxdb_client.InfluxDBClient(url=influx_url, token=token, org=org)
write_api = client.write_api(write_options=SYNCHRONOUS)

print(f"Starting data producer. Fetching from {sensor_api_url} and writing to InfluxDB at {influx_url}...")

# --- 5초마다 API에서 데이터를 가져와 InfluxDB에 전송 ---
try:
    while True:
        try:
            # 1. 목업 API 서버에서 데이터 가져오기
            response = requests.get(sensor_api_url)
            response.raise_for_status()  # 오류가 발생하면 예외를 발생시킴
            data = response.json()

            # 2. InfluxDB에 쓸 데이터 포인트(Point) 리스트 생성
            points = []

            # 2-1. 전력 데이터 (power_metrics)
            power_data = data.get("power_metrics", {})
            for source, metrics in power_data.items():
                point = influxdb_client.Point("power_metrics").tag("source", source)
                for field, value in metrics.items():
                    if value is not None:
                        point.field(field, value)
                points.append(point)

            # 2-2. 시스템 상태 데이터 (system_status)
            status_data = data.get("system_status", {})
            for component, metrics in status_data.items():
                point = influxdb_client.Point("system_status").tag("component", component)
                for field, value in metrics.items():
                    if value is not None:
                        point.field(field, value)
                points.append(point)

            # 2-3. 환경 센서 데이터 (environment_sensors)
            environment_data = data.get("environment_sensors", {})
            for sensor_type, value in environment_data.items():
                if value is not None:
                    point = influxdb_client.Point("environment_sensors").tag("type", sensor_type).field("value", value)
                    points.append(point)

            # 3. 데이터 쓰기
            if points:
                write_api.write(bucket=bucket, org=org, record=points)
                print(f"Successfully fetched and wrote {len(points)} points to InfluxDB.")
            else:
                print("No data to write.")

        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from API: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

        time.sleep(5)

except KeyboardInterrupt:
    print("\nExiting.")
finally:
    client.close()
