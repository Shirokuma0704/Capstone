#!/usr/bin/env python3
"""
InfluxDB에 저장된 센서 데이터 확인 스크립트
"""

import influxdb_client
from influxdb_client.client.query_api import QueryApi
import os

# InfluxDB 연결 설정
INFLUX_URL = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
INFLUX_TOKEN = os.getenv('INFLUXDB_TOKEN', 'my-super-secret-token')
INFLUX_ORG = os.getenv('INFLUXDB_ORG', 'my-org')
INFLUX_BUCKET = os.getenv('INFLUXDB_BUCKET', 'my-bucket')

print(f"InfluxDB 연결: {INFLUX_URL}")
print(f"Organization: {INFLUX_ORG}")
print(f"Bucket: {INFLUX_BUCKET}")
print("=" * 80)

# InfluxDB 클라이언트 초기화
try:
    client = influxdb_client.InfluxDBClient(
        url=INFLUX_URL,
        token=INFLUX_TOKEN,
        org=INFLUX_ORG
    )
    query_api = client.query_api()
    print("✅ InfluxDB 클라이언트 연결 완료\n")
except Exception as e:
    print(f"❌ InfluxDB 연결 실패: {e}")
    exit(1)

# 쿼리 실행
queries = {
    "power_metrics (최근 10개)": f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: -1h)
          |> filter(fn: (r) => r["_measurement"] == "power_metrics")
          |> limit(n: 10)
    ''',
    "environment_sensors (최근 10개)": f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: -1h)
          |> filter(fn: (r) => r["_measurement"] == "environment_sensors")
          |> limit(n: 10)
    '''
}

for query_name, query in queries.items():
    print(f"\n📊 {query_name}")
    print("-" * 80)

    try:
        tables = query_api.query(query)

        if not tables or all(len(table.records) == 0 for table in tables):
            print("⚠️  데이터가 없습니다.")
            continue

        count = 0
        for table in tables:
            for record in table.records:
                count += 1
                print(f"  {record.get_time()}: "
                      f"[{record.get_measurement()}] "
                      f"{record.get_field()}={record.get_value()} "
                      f"(tags: {record.values.get('source', '')} {record.values.get('type', '')})")

        print(f"\n✅ 총 {count}개 레코드 조회 완료")

    except Exception as e:
        print(f"❌ 쿼리 실행 실패: {e}")

print("\n" + "=" * 80)
print("데이터 확인 완료")

# 클라이언트 종료
client.close()
