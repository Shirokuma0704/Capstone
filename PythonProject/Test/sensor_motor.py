# solar_tracker_with_cache.py
import serial
import time
import json
import os
import pynmea2
import RPi.GPIO as GPIO
from datetime import datetime, timezone
from pysolar.solar import get_altitude, get_azimuth

# ============================================================
# 설정
# ============================================================

# GPS 설정
GPS_PORT = "/dev/serial0"
GPS_BAUD = 9600

# 캐시 파일 경로
CACHE_FILE = "/home/user/cache/solar_tracker_cache.json"

# 서보모터 핀 설정
SERVO_AZIMUTH_PIN = 18  # MG996R - 방위각 (수평 회전)
SERVO_ALTITUDE_PIN = 12  # MG995 - 고도각 (수직 회전)
PWM_FREQUENCY = 50

# 업데이트 주기 (초)
UPDATE_INTERVAL = 10  # 1분마다 태양 위치 업데이트

# 서보모터 각도 보정값
AZIMUTH_OFFSET = 90  # 방위각 오프셋 (0도가 정북일 때)
ALTITUDE_OFFSET = 0  # 고도각 오프셋

# GPS Fix 최대 대기 시간
GPS_FIX_TIMEOUT = 10  # 60초


# ============================================================
# 캐시 관리 클래스
# ============================================================

class CacheManager:
    def __init__(self, cache_file):
        self.cache_file = cache_file

    def load_cache(self):
        """캐시 로드"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
                print(f"✓ 캐시 로드 성공:")
                print(f"  - 위도: {cache['latitude']:.6f}°")
                print(f"  - 경도: {cache['longitude']:.6f}°")
                print(f"  - 마지막 업데이트: {cache['timestamp']}")
                return cache
            except Exception as e:
                print(f"⚠ 캐시 로드 실패: {e}")
                return None
        else:
            print("ℹ 캐시 파일 없음 (첫 실행)")
            return None

    def save_cache(self, latitude, longitude):
        """캐시 저장"""
        cache = {
            'latitude': latitude,
            'longitude': longitude,
            'timestamp': datetime.now().isoformat()
        }

        try:
            with open(self.cache_file, 'w') as f:
                json.dump(cache, f, indent=2)
            print(f"✓ 위치 정보 캐시 저장")
        except Exception as e:
            print(f"⚠ 캐시 저장 실패: {e}")


# ============================================================
# NTP 시간 동기화
# ============================================================

def sync_time_with_ntp():
    """NTP로 시스템 시간 동기화"""
    try:
        import ntplib
        ntp_client = ntplib.NTPClient()
        print("NTP 서버와 시간 동기화 중...")
        response = ntp_client.request('pool.ntp.org', version=3, timeout=5)

        ntp_time = datetime(response.tx_time)
        print(f"✓ NTP 시간: {ntp_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"  (오프셋: {response.offset * 1000:.2f}ms)")

        return True
    except ImportError:
        print("⚠ ntplib 미설치 (pip3 install ntplib)")
        return False
    except Exception as e:
        print(f"⚠ NTP 동기화 실패: {e}")
        return False


# ============================================================
# GPS 클래스 (캐시 지원)
# ============================================================

class GPSReader:
    def __init__(self, port, baud, cache_manager):
        self.port = port
        self.baud = baud
        self.cache_manager = cache_manager
        self.serial = None
        self.latitude = None
        self.longitude = None
        self.timestamp = None
        self.valid = False
        self.cached_position = None

    def connect(self):
        """GPS 연결"""
        try:
            self.serial = serial.Serial(self.port, self.baud, timeout=1)
            print(f"✓ GPS 연결 성공: {self.port}")
            return True
        except Exception as e:
            print(f"✗ GPS 연결 실패: {e}")
            return False

    def load_cached_position(self):
        """캐시된 위치 로드"""
        self.cached_position = self.cache_manager.load_cache()
        if self.cached_position:
            # 캐시를 현재 위치로 임시 설정
            self.latitude = self.cached_position['latitude']
            self.longitude = self.cached_position['longitude']
            self.timestamp = datetime.now(timezone.utc)
            self.valid = True
            print("✓ 캐시된 위치를 임시로 사용")
            return True
        return False

    def read_position(self, timeout=10):
        """GPS 위치 읽기"""
        start_time = time.time()

        print(f"GPS 위성 신호 수신 중... (최대 {timeout}초)")

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

                            # 새 위치를 캐시에 저장
                            self.cache_manager.save_cache(self.latitude, self.longitude)

                            elapsed = time.time() - start_time
                            print(f"✓ GPS Fix 획득! (소요 시간: {elapsed:.1f}초)")

                            return True

                    # 진행 상황 표시
                    elapsed = int(time.time() - start_time)
                    if elapsed % 5 == 0:  # 5초마다
                        print(f"  대기 중... {elapsed}/{timeout}초", end='\r')

                except Exception as e:
                    pass

        print(f"\n⚠ GPS Fix 실패 ({timeout}초 초과)")

        # GPS Fix 실패 시 캐시 사용
        if self.cached_position:
            print("→ 캐시된 위치 사용")
            self.latitude = self.cached_position['latitude']
            self.longitude = self.cached_position['longitude']
            self.timestamp = datetime.now(timezone.utc)
            self.valid = True
            return True

        return False

    def get_position(self):
        """현재 위치 반환"""
        return {
            'latitude': self.latitude,
            'longitude': self.longitude,
            'timestamp': self.timestamp,
            'valid': self.valid
        }

    def close(self):
        """연결 종료"""
        if self.serial:
            self.serial.close()


# ============================================================
# 서보모터 클래스
# ============================================================

class ServoController:
    def __init__(self, azimuth_pin, altitude_pin):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        self.azimuth_pin = azimuth_pin
        self.altitude_pin = altitude_pin

        # PWM 설정
        GPIO.setup(azimuth_pin, GPIO.OUT)
        GPIO.setup(altitude_pin, GPIO.OUT)

        self.azimuth_pwm = GPIO.PWM(azimuth_pin, PWM_FREQUENCY)
        self.altitude_pwm = GPIO.PWM(altitude_pin, PWM_FREQUENCY)

        self.azimuth_pwm.start(0)
        self.altitude_pwm.start(0)

        # 현재 각도 저장
        self.current_azimuth = 90
        self.current_altitude = 45

    def set_angle(self, pwm, angle):
        """각도 설정 (0-180도)"""
        angle = max(0, min(180, angle))
        duty_cycle = 2.5 + (angle / 180.0) * 10.0
        pwm.ChangeDutyCycle(duty_cycle)
        time.sleep(0.5)
        pwm.ChangeDutyCycle(0)  # 떨림 방지

    def move_to_position(self, azimuth, altitude):
        """태양 위치로 이동"""
        # 각도 제한 (0-180도)
        azimuth = max(0, min(180, azimuth))
        altitude = max(0, min(180, altitude))

        print(f"  서보모터 이동:")
        print(f"    방위각: {self.current_azimuth:.1f}° → {azimuth:.1f}°")
        print(f"    고도각: {self.current_altitude:.1f}° → {altitude:.1f}°")

        self.set_angle(self.azimuth_pwm, azimuth)
        self.set_angle(self.altitude_pwm, altitude)

        self.current_azimuth = azimuth
        self.current_altitude = altitude

    def reset_position(self):
        """초기 위치로 복귀 (동쪽 수평)"""
        print("  초기 위치로 복귀...")
        self.move_to_position(90, 45)

    def cleanup(self):
        """정리"""
        self.azimuth_pwm.stop()
        self.altitude_pwm.stop()
        GPIO.cleanup()


# ============================================================
# 태양 추적 시스템
# ============================================================

class SolarTracker:
    def __init__(self, gps_reader, servo_controller):
        self.gps = gps_reader
        self.servo = servo_controller
        self.last_update = None

    def calculate_solar_position(self, latitude, longitude, timestamp):
        """태양 위치 계산 (방위각, 고도각)"""
        try:
            # Pysolar를 사용한 태양 위치 계산
            altitude_deg = get_altitude(latitude, longitude, timestamp)
            azimuth_deg = get_azimuth(latitude, longitude, timestamp)

            return azimuth_deg, altitude_deg

        except Exception as e:
            print(f"✗ 태양 위치 계산 오류: {e}")
            return None, None

    def convert_to_servo_angles(self, azimuth_deg, altitude_deg):
        """천문학 각도를 서보모터 각도로 변환"""

        # 방위각 변환 (0-360° → 0-180°)
        if azimuth_deg < 0:
            azimuth_deg += 360

        # 90° (동쪽)를 기준으로 변환
        servo_azimuth = (azimuth_deg - 90) / 2 + 90
        servo_azimuth = max(0, min(180, servo_azimuth))

        # 고도각 변환 (0-90° → 0-90°)
        servo_altitude = altitude_deg
        servo_altitude = max(0, min(90, servo_altitude))

        return servo_azimuth, servo_altitude

    def is_daytime(self, altitude_deg):
        """낮인지 확인 (태양이 수평선 위에 있는지)"""
        return altitude_deg > 0

    def update(self):
        """태양 위치 업데이트 및 서보모터 제어"""
        print("\n" + "=" * 60)
        print(f"태양 추적 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        # GPS 위치 읽기
        if self.gps.read_position(timeout=GPS_FIX_TIMEOUT):
            pos = self.gps.get_position()

            print(f"✓ GPS 위치:")
            print(f"  위도: {pos['latitude']:.6f}°")
            print(f"  경도: {pos['longitude']:.6f}°")
            print(f"  시간: {pos['timestamp'].strftime('%Y-%m-%d %H:%M:%S UTC')}")

            # 태양 위치 계산
            azimuth, altitude = self.calculate_solar_position(
                pos['latitude'],
                pos['longitude'],
                pos['timestamp']
            )

            if azimuth is not None and altitude is not None:
                print(f"\n✓ 태양 위치:")
                print(f"  방위각: {azimuth:.2f}° (0°=북, 90°=동, 180°=남, 270°=서)")
                print(f"  고도각: {altitude:.2f}° (0°=수평선, 90°=천정)")

                # 낮/밤 확인
                if self.is_daytime(altitude):
                    print(f"  상태: 낮 (태양 가시)")

                    # 서보모터 각도 변환
                    servo_az, servo_alt = self.convert_to_servo_angles(azimuth, altitude)

                    print(f"\n✓ 서보모터 각도:")
                    print(f"  방위각 서보: {servo_az:.1f}°")
                    print(f"  고도각 서보: {servo_alt:.1f}°")

                    # 서보모터 이동
                    self.servo.move_to_position(servo_az, servo_alt)

                else:
                    print(f"  상태: 밤 (태양 불가시)")
                    print("  → 대기 위치로 이동")
                    self.servo.reset_position()

                self.last_update = time.time()
                return True

        else:
            print("✗ GPS 위치를 읽을 수 없습니다.")
            return False

    def run(self):
        """메인 루프 실행"""
        print("\n" + "╔" + "═" * 58 + "╗")
        print("║" + " " * 10 + "태양 추적 시스템 (캐시 지원)" + " " * 18 + "║")
        print("╚" + "═" * 58 + "╝\n")

        try:
            # 초기 위치로 이동
            print("초기화 중...")
            self.servo.reset_position()
            time.sleep(2)

            # 메인 루프
            while True:
                self.update()

                print(f"\n다음 업데이트까지 {UPDATE_INTERVAL}초 대기...")
                time.sleep(UPDATE_INTERVAL)

        except KeyboardInterrupt:
            print("\n\n시스템 종료 중...")
            self.servo.reset_position()

        finally:
            self.servo.cleanup()
            self.gps.close()
            print("✓ 태양 추적 시스템 종료 완료")


# ============================================================
# 메인 실행
# ============================================================

if __name__ == "__main__":
    print("\n" + "╔" + "═" * 58 + "╗")
    print("║" + " " * 8 + "태양 추적 시스템 - 빠른 시작 모드" + " " * 15 + "║")
    print("╚" + "═" * 58 + "╝\n")

    # 1. 캐시 매니저 초기화
    cache_mgr = CacheManager(CACHE_FILE)

    # 2. NTP 시간 동기화
    print("[1/5] 시간 동기화")
    print("-" * 60)
    sync_time_with_ntp()
    print()

    # 3. GPS 초기화
    print("[2/5] GPS 초기화")
    print("-" * 60)
    gps = GPSReader(GPS_PORT, GPS_BAUD, cache_mgr)
    if not gps.connect():
        print("✗ GPS 연결 실패. 프로그램을 종료합니다.")
        exit(1)
    print()

    # 4. 캐시된 위치 로드
    print("[3/5] 캐시 확인")
    print("-" * 60)
    has_cache = gps.load_cached_position()
    print()

    # 5. 서보모터 초기화
    print("[4/5] 서보모터 초기화")
    print("-" * 60)
    servo = ServoController(SERVO_AZIMUTH_PIN, SERVO_ALTITUDE_PIN)
    print("✓ 서보모터 준비 완료")
    print()

    # 6. 태양 추적 시작
    print("[5/5] 시스템 시작")
    print("-" * 60)
    if has_cache:
        print("✓ 캐시를 활용한 빠른 시작 준비 완료")
    else:
        print("ℹ 첫 실행: GPS Fix 대기 필요")
    print()

    tracker = SolarTracker(gps, servo)
    tracker.run()