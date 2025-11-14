# check_solar_position.py
from datetime import datetime, timezone
from pysolar.solar import get_altitude, get_azimuth

# 부산 위치
LATITUDE = 35.116452
LONGITUDE = 128.967377

print("=== 현재 태양 위치 확인 ===\n")

now = datetime.now(timezone.utc)
local_time = datetime.now()

azimuth = get_azimuth(LATITUDE, LONGITUDE, now)
altitude = get_altitude(LATITUDE, LONGITUDE, now)

print(f"위치: {LATITUDE:.6f}°N, {LONGITUDE:.6f}°E")
print(f"현지 시간: {local_time.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"UTC 시간: {now.strftime('%Y-%m-%d %H:%M:%S')}")
print()
print(f"태양 방위각: {azimuth:.2f}°")
print(f"  (0°=북, 90°=동, 180°=남, 270°=서)")
print(f"태양 고도각: {altitude:.2f}°")
print(f"  (0°=수평선, 90°=천정)")
print()

if altitude > 0:
    print("✓ 태양이 수평선 위에 있습니다 (낮)")
else:
    print("✗ 태양이 수평선 아래에 있습니다 (밤)")