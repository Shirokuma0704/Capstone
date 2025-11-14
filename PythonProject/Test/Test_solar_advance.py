# solar_position_monitor.py
import serial
import time
import pynmea2
from datetime import datetime, timezone
from pysolar.solar import get_altitude, get_azimuth

# GPS 설정
GPS_PORT = "/dev/serial0"
GPS_BAUD = 9600

# 업데이트 주기 (초)
UPDATE_INTERVAL = 10


class GPSReader:
    def __init__(self, port, baud):
        self.port = port
        self.baud = baud
        self.serial = None
        self.latitude = None
        self.longitude = None
        self.timestamp = None
        self.valid = False

    def connect(self):
        """GPS 연결"""
        try:
            self.serial = serial.Serial(self.port, self.baud, timeout=1)
            print(f"✓ GPS 연결 성공: {self.port}\n")
            return True
        except Exception as e:
            print(f"✗ GPS 연결 실패: {e}")
            return False

    def read_position(self, timeout=10):
        """GPS 위치 읽기"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            if self.serial.in_waiting > 0:
                try:
                    line = self.serial.readline().decode('ascii', errors='replace').strip()

                    if line.startswith('$GPRMC') or line.startswith('$GNRMC'):
                        msg = pynmea2.parse(line)

                        if msg.status == 'A':  # 유효한 데이터
                            self.latitude = msg.latitude
                            self.longitude = msg.longitude
                            self.timestamp = datetime.combine(
                                msg.datestamp,
                                msg.timestamp
                            ).replace(tzinfo=timezone.utc)
                            self.valid = True
                            return True

                except Exception as e:
                    pass

        return False

    def close(self):
        """연결 종료"""
        if self.serial:
            self.serial.close()


def calculate_solar_position(latitude, longitude, timestamp):
    """태양 위치 계산"""
    try:
        altitude_deg = get_altitude(latitude, longitude, timestamp)
        azimuth_deg = get_azimuth(latitude, longitude, timestamp)
        return azimuth_deg, altitude_deg
    except Exception as e:
        print(f"✗ 태양 위치 계산 오류: {e}")
        return None, None


def get_direction_text(azimuth):
    """방위각을 방향 텍스트로 변환"""
    directions = [
        ("북", 0, 22.5),
        ("북동", 22.5, 67.5),
        ("동", 67.5, 112.5),
        ("남동", 112.5, 157.5),
        ("남", 157.5, 202.5),
        ("남서", 202.5, 247.5),
        ("서", 247.5, 292.5),
        ("북서", 292.5, 337.5),
        ("북", 337.5, 360)
    ]

    for direction, min_angle, max_angle in directions:
        if min_angle <= azimuth < max_angle:
            return direction
    return "북"


def convert_to_servo_angles(azimuth_deg, altitude_deg):
    """천문학 각도를 서보모터 각도로 변환 (시뮬레이션)"""
    if azimuth_deg < 0:
        azimuth_deg += 360

    # 방위각: 동쪽(90°)을 기준으로 0-180° 범위로 변환
    servo_azimuth = (azimuth_deg - 90) / 2 + 90
    servo_azimuth = max(0, min(180, servo_azimuth))

    # 고도각: 0-90° 범위로 제한
    servo_altitude = max(0, min(90, altitude_deg))

    return servo_azimuth, servo_altitude


def display_solar_info(gps_reader):
    """태양 위치 정보 표시"""
    print("\n" + "=" * 70)
    print(f"측정 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S KST')}")
    print("=" * 70)

    # GPS 위치 읽기
    print("\n[1] GPS 위치 읽는 중...")
    if gps_reader.read_position(timeout=10):
        lat = gps_reader.latitude
        lon = gps_reader.longitude
        timestamp = gps_reader.timestamp

        print(f"    ✓ 위도: {lat:.6f}°")
        print(f"    ✓ 경도: {lon:.6f}°")
        print(f"    ✓ UTC 시간: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

        # 태양 위치 계산
        print("\n[2] 태양 위치 계산 중...")
        azimuth, altitude = calculate_solar_position(lat, lon, timestamp)

        if azimuth is not None and altitude is not None:
            direction = get_direction_text(azimuth)

            print(f"    ✓ 방위각: {azimuth:.2f}° ({direction})")
            print(f"    ✓ 고도각: {altitude:.2f}°")

            # 태양 상태 판단
            print("\n[3] 태양 상태:")
            if altitude > 0:
                print(f"    ✓ 낮 - 태양이 수평선 위에 있습니다")
                print(f"    ✓ 태양 고도: 수평선으로부터 {altitude:.2f}° 위")
            else:
                print(f"    ✗ 밤 - 태양이 수평선 아래에 있습니다")
                print(f"    ✗ 태양 고도: 수평선으로부터 {abs(altitude):.2f}° 아래")

            # 서보모터 각도 시뮬레이션
            print("\n[4] 서보모터 제어 시뮬레이션:")
            if altitude > 0:
                servo_az, servo_alt = convert_to_servo_angles(azimuth, altitude)

                print(f"    → 방위각 서보: {servo_az:.1f}° (0°=동쪽, 90°=남쪽, 180°=서쪽)")
                print(f"    → 고도각 서보: {servo_alt:.1f}° (0°=수평, 90°=천정)")

                # 시각적 표현
                print("\n    서보모터 위치 시각화:")
                print(f"    방위각: {'░' * int(servo_az / 10)}█{'░' * (18 - int(servo_az / 10))} {servo_az:.0f}°")
                print(f"    고도각: {'░' * int(servo_alt / 10)}█{'░' * (9 - int(servo_alt / 10))} {servo_alt:.0f}°")
            else:
                print(f"    → 대기 위치: 방위각=90°, 고도각=0° (수평 동쪽)")

            # 추가 정보
            print("\n[5] 추가 정보:")

            # 일출/일몰 추정
            if altitude > 0:
                if altitude < 10:
                    print(f"    ⚠ 일출 직후 또는 일몰 직전 (낮은 고도)")
                elif altitude > 60:
                    print(f"    ☀ 한낮 (높은 고도)")
                else:
                    print(f"    ☀ 정상 추적 가능 범위")

            # 계절 정보
            local_time = datetime.now()
            month = local_time.month
            if month in [12, 1, 2]:
                season = "겨울 (태양 고도 낮음)"
            elif month in [3, 4, 5]:
                season = "봄"
            elif month in [6, 7, 8]:
                season = "여름 (태양 고도 높음)"
            else:
                season = "가을"
            print(f"    🗓 계절: {season}")

            return True
        else:
            print("    ✗ 태양 위치 계산 실패")
            return False
    else:
        print("    ✗ GPS 위치를 읽을 수 없습니다")
        return False


def main():
    print("\n" + "╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "태양 위치 모니터링 시스템" + " " * 26 + "║")
    print("║" + " " * 20 + "(서보모터 제외)" + " " * 27 + "║")
    print("╚" + "═" * 68 + "╝")

    # GPS 연결
    gps = GPSReader(GPS_PORT, GPS_BAUD)
    if not gps.connect():
        print("GPS 연결 실패. 프로그램을 종료합니다.")
        return

    try:
        while True:
            display_solar_info(gps)

            print(f"\n{'─' * 70}")
            print(f"다음 업데이트까지 {UPDATE_INTERVAL}초 대기... (Ctrl+C로 종료)")
            print(f"{'─' * 70}")

            time.sleep(UPDATE_INTERVAL)

    except KeyboardInterrupt:
        print("\n\n프로그램 종료")

    finally:
        gps.close()
        print("✓ GPS 연결 종료")


if __name__ == "__main__":
    main()