# ============================================================
# solar_tracker_full.py
# GPS 기반 태양 추적 + RTC(DS3231) 백업 + 캐시 기능 + 센서 통합
#
# 센서 포함:
# - GPS (NEO-6M)
# - RTC (DS3231)
# - 온습도 센서 (DHT11)
# - 전류/전압 센서 (INA219)
# - 서보모터 (MG996R, MG995)
#
# ============================================================

import serial
import time
import json
import os
import threading
import pynmea2
import RPi.GPIO as GPIO
from datetime import datetime, timezone

# 태양 위치 계산 라이브러리
from pysolar.solar import get_altitude, get_azimuth

# 추가 센서
import adafruit_dht
import board
from smbus2 import SMBus

# ============================================================
# 설정
# ============================================================

GPS_PORT = "/dev/serial0"
GPS_BAUD = 9600

CACHE_FILE = "/home/user/cache/solar_tracker_cache.json"

SERVO_AZIMUTH_PIN = 18   # 방위각 서보 (MG996R)
SERVO_ALTITUDE_PIN = 12  # 고도각 서보 (MG995)

PWM_FREQUENCY = 50
UPDATE_INTERVAL = 60   # 1분 간격

AZIMUTH_OFFSET = 90
ALTITUDE_OFFSET = 0

GPS_FIX_TIMEOUT = 60  # GPS Fix 최대 대기
MANUAL_HOLD_SECONDS = 180  # 수동 명령 유지 시간

# INA219 I2C 우선순위 (software I2C 버스 3 → 기본 버스 1 순으로 시도)
INA219_BUS_PRIORITY = [
    int(x) for x in os.getenv("INA219_BUS_PRIORITY", "3,1").split(",") if x.strip()
]
INA219_ADDRESS = int(os.getenv("INA219_ADDRESS", "0x40"), 0)
# 기본 캘리브레이션 값 (0이면 Current/Power 레지스터가 작동하지 않음)
INA219_CALIBRATION = int(os.getenv("INA219_CALIBRATION", "4096"))
# 기본 션트 저항(Ω) — 모듈이 0.1Ω일 때 4096 캘리브레이션 값이 잘 맞음
INA219_SHUNT_OHMS = float(os.getenv("INA219_SHUNT_OHMS", "0.1"))

# DHT11 설정 (adafruit_dht 사용)
try:
    DHT_PIN = board.D17
    dht_device = adafruit_dht.DHT11(DHT_PIN)
except Exception as e:
    print(f"⚠ DHT11 초기화 실패: {e}")
    DHT_PIN = None
    dht_device = None


class INA219Reader:
    """INA219를 smbus(I2C 버스 번호 우선순위)로만 읽어오는 헬퍼"""

    def __init__(self):
        self.address = INA219_ADDRESS
        self.cal_value = INA219_CALIBRATION
        self.shunt_ohms = INA219_SHUNT_OHMS
        self.mode = None
        self.device = None  # smbus 핸들
        self.bus_num = None

        for bus_candidate in INA219_BUS_PRIORITY:
            try:
                bus = SMBus(bus_candidate)
                self.device = bus
                self.bus_num = bus_candidate
                self.mode = "smbus"
                self._write_register(0x05, self.cal_value)  # Calibration 강제 설정
                print(f"✓ INA219 SMBus({bus_candidate}) 준비 완료 (cal={self.cal_value})")
                return
            except Exception as e:
                print(f"⚠ INA219 SMBus {bus_candidate} 초기화 실패: {e}")

        print("✗ INA219 초기화 실패 (사용 불가)")

    def _write_register(self, reg, value):
        """INA219는 Big-endian을 사용하므로 바이트 스왑 후 기록"""
        if self.mode != "smbus":
            return
        try:
            swapped = ((value & 0xFF) << 8) | (value >> 8)
            self.device.write_word_data(self.address, reg, swapped)
        except Exception as e:
            print(f"  ✗ INA219 레지스터 0x{reg:02X} 쓰기 실패: {e}")

    def _read_register(self, reg):
        """INA219 16비트 레지스터 읽기 (Big-endian → 리틀 변환)"""
        if self.mode != "smbus":
            return None
        try:
            val = self.device.read_word_data(self.address, reg)
            return ((val & 0xFF) << 8) | (val >> 8)
        except Exception as e:
            print(f"  ✗ INA219 레지스터 0x{reg:02X} 읽기 실패: {e}")
            return None

    @staticmethod
    def _signed(val):
        if val is None:
            return None
        return val - 65536 if val > 32767 else val

    def read(self):
        """전압(V), 전류(A), 전력(W) 튜플 반환"""
        if self.mode == "smbus":
            try:
                bus_voltage_raw = self._read_register(0x02)
                current_raw = self._signed(self._read_register(0x04))
                power_raw = self._read_register(0x03)

                if bus_voltage_raw is None or current_raw is None:
                    return None, None, None

                voltage = (bus_voltage_raw >> 3) * 0.004  # 4 mV per bit

                current_lsb = 0.04096 / (self.cal_value * self.shunt_ohms)
                current = current_raw * current_lsb  # A

                power = None
                if power_raw is not None:
                    power = power_raw * current_lsb * 20  # Power LSB = 20 * current LSB

                return voltage, current, power
            except Exception as e:
                print(f"  ✗ INA219 오류(SMBus): {e}")
                return None, None, None

        return None, None, None


ina219_reader = INA219Reader()

# RTC 주소
DS3231_ADDR = 0x68


# ============================================================
# DS3231 시간 읽기
# ============================================================

def bcd_to_dec(bcd):
    return (bcd & 0x0F) + ((bcd >> 4) * 10)


def read_time_ds3231():
    """RTC DS3231 시간 읽기"""
    try:
        bus = SMBus(1)
        data = bus.read_i2c_block_data(DS3231_ADDR, 0x00, 7)
        bus.close()

        sec = bcd_to_dec(data[0])
        minute = bcd_to_dec(data[1])
        hour = bcd_to_dec(data[2])
        day = bcd_to_dec(data[4])
        month = bcd_to_dec(data[5])
        year = bcd_to_dec(data[6]) + 2000

        return datetime(year, month, day, hour, minute, sec, tzinfo=timezone.utc)

    except Exception as e:
        print(f"⚠ RTC 읽기 실패: {e}")
        return None


# ============================================================
# 캐시 관리
# ============================================================

class CacheManager:
    def __init__(self, cache_file):
        self.cache_file = cache_file

    def load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)

                print(f"✓ 캐시 로드 성공")
                print(f"  - 위도: {cache['latitude']}")
                print(f"  - 경도: {cache['longitude']}")
                return cache

            except Exception as e:
                print(f"⚠ 캐시 읽기 실패: {e}")
                return None

        print("ℹ 캐시 없음")
        return None

    def save_cache(self, latitude, longitude):
        data = {
            'latitude': latitude,
            'longitude': longitude,
            'timestamp': datetime.now().isoformat()
        }

        try:
            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)
            print("✓ 캐시 저장 완료")
        except Exception as e:
            print(f"⚠ 캐시 저장 실패: {e}")


# ============================================================
# GPS 처리
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
        try:
            self.serial = serial.Serial(self.port, self.baud, timeout=1)
            print(f"✓ GPS 연결됨: {self.port}")
            return True
        except Exception as e:
            print(f"✗ GPS 연결 실패: {e}")
            return False

    def load_cached_position(self):
        self.cached_position = self.cache_manager.load_cache()
        if self.cached_position:
            self.latitude = self.cached_position['latitude']
            self.longitude = self.cached_position['longitude']
            self.timestamp = datetime.now(timezone.utc)
            self.valid = True
            print("✓ 캐시 기반 임시 위치 사용")
            return True
        return False

    def read_position(self, timeout=GPS_FIX_TIMEOUT):
        print(f"GPS Fix 시도 중… 최대 {timeout}초")
        start = time.time()

        while time.time() - start < timeout:
            if self.serial.in_waiting > 0:
                try:
                    line = self.serial.readline().decode("ascii", errors="replace").strip()
                    if line.startswith("$GPRMC") or line.startswith("$GNRMC"):
                        msg = pynmea2.parse(line)

                        if msg.status == "A":
                            self.latitude = msg.latitude
                            self.longitude = msg.longitude
                            self.timestamp = datetime.combine(msg.datestamp, msg.timestamp).replace(
                                tzinfo=timezone.utc
                            )
                            self.valid = True

                            self.cache_manager.save_cache(self.latitude, self.longitude)
                            print("✓ GPS Fix 성공")
                            return True

                except Exception:
                    pass

        print("⚠ GPS Fix 실패 → 캐시 사용")
        if self.cached_position:
            self.valid = True
            self.latitude = self.cached_position['latitude']
            self.longitude = self.cached_position['longitude']
            self.timestamp = datetime.now(timezone.utc)
            return True

        return False

    def get_position(self):
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timestamp": self.timestamp,
            "valid": self.valid,
        }

    def close(self):
        if self.serial:
            self.serial.close()


# ============================================================
# 서보모터
# ============================================================

class ServoController:
    def __init__(self, azimuth_pin, altitude_pin):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        GPIO.setup(azimuth_pin, GPIO.OUT)
        GPIO.setup(altitude_pin, GPIO.OUT)

        self.pwm_az = GPIO.PWM(azimuth_pin, PWM_FREQUENCY)
        self.pwm_alt = GPIO.PWM(altitude_pin, PWM_FREQUENCY)

        self.pwm_az.start(0)
        self.pwm_alt.start(0)

        self.current_az = 90
        self.current_alt = 45

    def set_angle(self, pwm, angle):
        angle = max(0, min(180, angle))
        duty = 2.5 + (angle / 180) * 10
        pwm.ChangeDutyCycle(duty)
        time.sleep(0.4)
        pwm.ChangeDutyCycle(0)

    def move_to_position(self, azimuth, altitude):
        print(f"  → 서보 이동: AZ {azimuth:.1f}°, ALT {altitude:.1f}°")
        self.set_angle(self.pwm_az, azimuth)
        self.set_angle(self.pwm_alt, altitude)

        self.current_az = azimuth
        self.current_alt = altitude

    def reset_position(self):
        print("  초기 위치로 복귀")
        self.move_to_position(90, 45)

    def cleanup(self):
        self.pwm_az.stop()
        self.pwm_alt.stop()
        GPIO.cleanup()


class NoOpServoController:
    """하드웨어가 없을 때를 위한 더미 서보 컨트롤러"""

    def __init__(self):
        self.current_az = 90
        self.current_alt = 45

    def move_to_position(self, azimuth, altitude):
        print(f"  → (더미) 서보 이동: AZ {azimuth:.1f}°, ALT {altitude:.1f}°")
        self.current_az = azimuth
        self.current_alt = altitude

    def reset_position(self):
        print("  (더미) 초기 위치로 복귀")
        self.move_to_position(90, 45)

    def cleanup(self):
        pass


# ============================================================
# 태양 추적 시스템
# ============================================================

class SolarTracker:
    def __init__(self, gps_reader, servo_controller):
        self.gps = gps_reader
        self.servo = servo_controller
        self.manual_override_until = 0
        self.latest_status = {
            "power_metrics": {
                "solar_panel": {"voltage": None, "current": None, "power": None}
            },
            "system_status": {
                "tracker": {
                    "motor_x_angle": self.servo.current_az,
                    "motor_y_angle": self.servo.current_alt,
                    "mode": "idle"
                },
                "environment": {"temperature": None, "humidity": None},
                "controller": {"last_update": None},
                "gps": {"latitude": None, "longitude": None, "timestamp": None}
            }
        }

    def calculate_solar_position(self, latitude, longitude, timestamp):
        try:
            altitude = get_altitude(latitude, longitude, timestamp)
            azimuth = get_azimuth(latitude, longitude, timestamp)
            return azimuth, altitude
        except:
            return None, None

    def is_daytime(self, altitude):
        return altitude > 0

    def convert_to_servo(self, az_deg, alt_deg):

        if az_deg < 0:
            az_deg += 360

        servo_az = (az_deg - 90) / 2 + 90
        servo_az = max(0, min(180, servo_az))

        servo_alt = max(0, min(90, alt_deg))

        return servo_az, servo_alt

    def manual_override_active(self):
        return time.time() < self.manual_override_until

    def set_manual_position(self, x_angle, y_angle, hold_seconds=MANUAL_HOLD_SECONDS):
        """외부 명령으로 모터 각도를 설정하고 일정 시간 자동 추적을 정지"""
        self.manual_override_until = time.time() + max(1, hold_seconds)
        self.servo.move_to_position(x_angle, y_angle)
        self.latest_status["system_status"]["tracker"].update(
            {"motor_x_angle": x_angle, "motor_y_angle": y_angle, "mode": "manual"}
        )
        self.latest_status["system_status"]["controller"]["last_update"] = datetime.now(timezone.utc).isoformat()

    def resume_auto(self):
        """즉시 자동 추적 모드로 복귀"""
        self.manual_override_until = 0
        self.latest_status["system_status"]["tracker"]["mode"] = "auto"

    def _read_environment(self):
        """DHT11 센서 읽기 (값이 없으면 None 유지)"""
        temperature = None
        humidity = None
        if dht_device is None:
            print("  ✗ DHT11 미초기화(하드웨어 미검출)")
            return temperature, humidity
        try:
            temperature = dht_device.temperature
            humidity = dht_device.humidity
        except RuntimeError as e:
            print(f"  ✗ DHT11 읽기 오류: {e.args[0]}")
        except Exception as e:
            print(f"  ✗ DHT11 실패: {e}")
        return temperature, humidity

    def _read_power(self):
        """INA219 전압/전류 읽기 (값이 없으면 None 유지)"""
        voltage = None
        current = None
        power = None
        if ina219_reader is None or ina219_reader.mode is None:
            print("  ✗ INA219 미초기화(하드웨어 미검출)")
            return voltage, current, power
        voltage, current, power = ina219_reader.read()
        if all(v is None for v in (voltage, current, power)):
            print("  ✗ INA219 데이터 없음")
        return voltage, current, power

    def _update_latest_status(self, env, power, latitude=None, longitude=None, timestamp=None, mode="auto"):
        """대시보드/API 응답용 최신 상태 저장"""
        temperature, humidity = env
        voltage, current, watt = power

        self.latest_status["power_metrics"]["solar_panel"] = {
            "voltage": voltage,
            "current": current,
            "power": watt
        }
        self.latest_status["system_status"]["environment"] = {
            "temperature": temperature,
            "humidity": humidity
        }
        self.latest_status["system_status"]["tracker"].update(
            {
                "motor_x_angle": self.servo.current_az,
                "motor_y_angle": self.servo.current_alt,
                "mode": mode
            }
        )
        self.latest_status["system_status"]["gps"] = {
            "latitude": latitude,
            "longitude": longitude,
            "timestamp": timestamp.isoformat() if isinstance(timestamp, datetime) else None
        }
        self.latest_status["system_status"]["controller"]["last_update"] = datetime.now(timezone.utc).isoformat()

    def get_latest_status(self):
        """외부 API에서 사용"""
        return self.latest_status

    def update(self):

        print("\n" + "=" * 60)
        print("🌞 태양 추적 업데이트")
        print("=" * 60)

        gps_ok = self.gps.read_position()

        if gps_ok:
            pos = self.gps.get_position()
            latitude = pos["latitude"]
            longitude = pos["longitude"]
            timestamp = pos["timestamp"]

        else:
            print("\n⚠ GPS Fix 실패 → RTC 기반 계산 모드")

            timestamp = read_time_ds3231()

            if timestamp is None:
                print("✗ RTC 시간 없음 → 추적 중단")
                return False

            if self.gps.cached_position:
                latitude = self.gps.cached_position["latitude"]
                longitude = self.gps.cached_position["longitude"]
                print(f"  ✓ 캐시 위치 사용 lat={latitude}, lon={longitude}")
            else:
                print("✗ 위치 정보 없음 → 초기 위치 유지")
                self.servo.reset_position()
                env = self._read_environment()
                power = self._read_power()
                self._update_latest_status(env, power, mode="error")
                return False

        # 수동 제어가 활성화된 경우 위치는 유지하고 센서만 갱신
        if self.manual_override_active():
            print("  상태: 수동 제어 유지 중 → 자동 추적 건너뜀")
            env = self._read_environment()
            power = self._read_power()
            self._update_latest_status(env, power, latitude, longitude, timestamp, mode="manual")
            return True

        # 태양 위치 계산
        az, alt = self.calculate_solar_position(latitude, longitude, timestamp)
        if az is None:
            print("✗ 태양 위치 계산 실패")
            env = self._read_environment()
            power = self._read_power()
            self._update_latest_status(env, power, latitude, longitude, timestamp, mode="error")
            return False

        print(f"  태양 방위각: {az:.2f}°")
        print(f"  태양 고도각: {alt:.2f}°")

        if self.is_daytime(alt):
            print("  상태: 낮")
            servo_az, servo_alt = self.convert_to_servo(az, alt)
            self.servo.move_to_position(servo_az, servo_alt)
            mode = "auto"
        else:
            print("  상태: 밤 → 초기 위치로 이동")
            self.servo.reset_position()
            mode = "night"

        # ============================================================
        # DHT11 추가
        # ============================================================
        print("\n[센서] 온습도 측정")
        env = self._read_environment()
        if all(v is not None for v in env):
            print(f"  온도: {env[0]:.1f}°C")
            print(f"  습도: {env[1]:.1f}%")
        else:
            print("  ✗ DHT11 데이터 없음")

        # ============================================================
        # INA219 추가
        # ============================================================
        print("\n[센서] 전류/전압 측정")
        power = self._read_power()
        if all(v is not None for v in power):
            print(f"  전압: {power[0]:.2f}V")
            print(f"  전류: {power[1]:.3f}A")
            print(f"  전력: {power[2]:.3f}W")

        self._update_latest_status(env, power, latitude, longitude, timestamp, mode=mode)
        return True

    def start_background(self):
        """별도 스레드에서 주기적 추적"""
        def loop():
            print("백그라운드 추적 스레드 시작")
            self.servo.reset_position()
            time.sleep(2)
            while True:
                try:
                    self.update()
                except Exception as e:
                    print(f"백그라운드 업데이트 오류: {e}")
                time.sleep(UPDATE_INTERVAL)

        thread = threading.Thread(target=loop, daemon=True)
        thread.start()
        return thread

    def run(self):
        print("\n╔═══════════════════════════════════════════════╗")
        print("║            🌞 태양 추적 시스템 시작            ║")
        print("╚═══════════════════════════════════════════════╝\n")

        self.servo.reset_position()
        time.sleep(2)

        while True:
            self.update()
            print(f"\n다음 업데이트까지 {UPDATE_INTERVAL}초 대기…")
            time.sleep(UPDATE_INTERVAL)


# ============================================================
# 메인 실행
# ============================================================

if __name__ == "__main__":

    cache_mgr = CacheManager(CACHE_FILE)

    gps = GPSReader(GPS_PORT, GPS_BAUD, cache_mgr)
    gps.connect()
    gps.load_cached_position()

    servo = ServoController(SERVO_AZIMUTH_PIN, SERVO_ALTITUDE_PIN)
    tracker = SolarTracker(gps, servo)

    try:
        tracker.run()
    except KeyboardInterrupt:
        servo.cleanup()
        gps.close()
        print("프로그램 종료됨.")
