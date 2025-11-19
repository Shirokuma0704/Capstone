"""Sun-tracking servo controller based on GPS + RTC with caching.

Adapted from src/Motor_GPS.py to run inside the PythonProject package.
Defaults target the docker-compose stack and hardware pin layout used on the Pi.
"""

from __future__ import annotations

import json
import os
import pathlib
import time
from datetime import datetime, timezone
from typing import Optional, Tuple

import pynmea2  # type: ignore
import RPi.GPIO as GPIO  # type: ignore
import serial  # type: ignore
from pysolar.solar import get_altitude, get_azimuth  # type: ignore
from smbus2 import SMBus  # type: ignore

# Optional hardware libs
try:
    import adafruit_extended_bus as exbus  # type: ignore
except Exception:  # pragma: no cover - hardware dependent
    exbus = None
try:
    import board  # type: ignore
    import busio  # type: ignore
    from adafruit_ina219 import INA219  # type: ignore
except Exception:  # pragma: no cover - hardware dependent
    board = None
    busio = None
    INA219 = None  # type: ignore
try:
    import adafruit_dht  # type: ignore
except Exception:  # pragma: no cover - hardware dependent
    adafruit_dht = None  # type: ignore

# Defaults (can be overridden via environment variables)
GPS_PORT = os.getenv("GPS_PORT", "/dev/serial0")
GPS_BAUD = int(os.getenv("GPS_BAUD", "9600"))
SERVO_AZIMUTH_PIN = int(os.getenv("SERVO_AZIMUTH_PIN", "18"))
SERVO_ALTITUDE_PIN = int(os.getenv("SERVO_ALTITUDE_PIN", "12"))
DHT_PIN_NAME = os.getenv("DHT_PIN", "D17")  # board pin name for adafruit_dht
DHT_SENSOR_KIND = os.getenv("DHT_SENSOR", "DHT11")
I2C_BUS_NUM = int(os.getenv("I2C_BUS", "3"))
UPDATE_INTERVAL = int(os.getenv("TRACK_INTERVAL", "60"))
AZIMUTH_OFFSET = float(os.getenv("AZIMUTH_OFFSET", "90"))
ALTITUDE_OFFSET = float(os.getenv("ALTITUDE_OFFSET", "0"))
PWM_FREQUENCY = 50
GPS_FIX_TIMEOUT = int(os.getenv("GPS_FIX_TIMEOUT", "60"))

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE_FILE = os.getenv(
    "SOLAR_CACHE_FILE", str(PROJECT_ROOT / "cache" / "solar_tracker_cache.json")
)


def _ensure_cache_dir(path: str) -> None:
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)


def _bcd_to_dec(bcd: int) -> int:
    return (bcd & 0x0F) + ((bcd >> 4) * 10)


def read_time_ds3231() -> Optional[datetime]:
    """RTC DS3231 시간 읽기."""
    try:
        bus = SMBus(1)
        data = bus.read_i2c_block_data(0x68, 0x00, 7)
        bus.close()

        sec = _bcd_to_dec(data[0])
        minute = _bcd_to_dec(data[1])
        hour = _bcd_to_dec(data[2])
        day = _bcd_to_dec(data[4])
        month = _bcd_to_dec(data[5])
        year = _bcd_to_dec(data[6]) + 2000

        return datetime(year, month, day, hour, minute, sec, tzinfo=timezone.utc)
    except Exception as exc:
        print(f"⚠ RTC 읽기 실패: {exc}")
        return None


class CacheManager:
    def __init__(self, cache_file: str):
        self.cache_file = cache_file
        _ensure_cache_dir(cache_file)

    def load_cache(self) -> Optional[dict]:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r") as f:
                    cache = json.load(f)
                print("✓ 캐시 로드 성공")
                return cache
            except Exception as exc:
                print(f"⚠ 캐시 읽기 실패: {exc}")
        else:
            print("ℹ 캐시 없음")
        return None

    def save_cache(self, latitude: float, longitude: float) -> None:
        data = {"latitude": latitude, "longitude": longitude, "timestamp": datetime.now().isoformat()}
        try:
            with open(self.cache_file, "w") as f:
                json.dump(data, f, indent=2)
            print("✓ 캐시 저장 완료")
        except Exception as exc:
            print(f"⚠ 캐시 저장 실패: {exc}")


class GPSReader:
    def __init__(self, port: str, baud: int, cache_manager: CacheManager):
        self.port = port
        self.baud = baud
        self.cache_manager = cache_manager

        self.serial = None
        self.latitude: Optional[float] = None
        self.longitude: Optional[float] = None
        self.timestamp: Optional[datetime] = None
        self.valid = False
        self.cached_position = None

    def connect(self) -> bool:
        try:
            self.serial = serial.Serial(self.port, self.baud, timeout=1)
            print(f"✓ GPS 연결됨: {self.port}")
            return True
        except Exception as exc:
            print(f"✗ GPS 연결 실패: {exc}")
            return False

    def load_cached_position(self) -> bool:
        self.cached_position = self.cache_manager.load_cache()
        if self.cached_position:
            self.latitude = self.cached_position["latitude"]
            self.longitude = self.cached_position["longitude"]
            self.timestamp = datetime.now(timezone.utc)
            self.valid = True
            print("✓ 캐시 기반 임시 위치 사용")
            return True
        return False

    def read_position(self, timeout: int = GPS_FIX_TIMEOUT) -> bool:
        if not self.serial:
            return False
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
            self.latitude = self.cached_position["latitude"]
            self.longitude = self.cached_position["longitude"]
            self.timestamp = datetime.now(timezone.utc)
            return True
        return False

    def get_position(self) -> dict:
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timestamp": self.timestamp,
            "valid": self.valid,
        }

    def close(self) -> None:
        if self.serial:
            self.serial.close()


class ServoController:
    def __init__(self, azimuth_pin: int, altitude_pin: int):
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

    def _set_angle(self, pwm, angle: float) -> None:
        angle = max(0, min(180, angle))
        duty = 2.5 + (angle / 180) * 10
        pwm.ChangeDutyCycle(duty)
        time.sleep(0.4)
        pwm.ChangeDutyCycle(0)

    def move_to_position(self, azimuth: float, altitude: float) -> None:
        print(f"  → 서보 이동: AZ {azimuth:.1f}°, ALT {altitude:.1f}°")
        self._set_angle(self.pwm_az, azimuth)
        self._set_angle(self.pwm_alt, altitude)
        self.current_az = azimuth
        self.current_alt = altitude

    def reset_position(self) -> None:
        print("  초기 위치로 복귀")
        self.move_to_position(90, 45)

    def cleanup(self) -> None:
        self.pwm_az.stop()
        self.pwm_alt.stop()
        GPIO.cleanup()


class PowerSensor:
    """INA219 wrapper with explicit I2C bus selection."""

    def __init__(self, bus_num: int):
        self.bus_num = bus_num
        self.ina = None
        self._setup()

    def _setup(self):
        if INA219 is None:
            print("INA219 라이브러리가 로드되지 않았습니다.")
            return
        try:
            i2c = None
            if self.bus_num and exbus:
                i2c = exbus.ExtendedI2C(self.bus_num)
            elif board and busio:
                i2c = busio.I2C(board.SCL, board.SDA)
            else:
                print("I2C 초기화 실패: board/busio 사용 불가.")
                return
            self.ina = INA219(i2c)
        except Exception as exc:  # pragma: no cover - hardware dependent
            print(f"INA219 초기화 실패: {exc}")
            self.ina = None

    def read(self) -> Optional[Tuple[float, float, float]]:
        if not self.ina:
            return None
        try:
            voltage = self.ina.bus_voltage
            current = self.ina.current / 1000  # mA -> A
            power = self.ina.power / 1000
            return voltage, current, power
        except Exception as exc:
            print(f"INA219 읽기 실패: {exc}")
            return None


class SolarTracker:
    def __init__(self, gps_reader: GPSReader, servo_controller: ServoController, power_sensor: PowerSensor):
        self.gps = gps_reader
        self.servo = servo_controller
        self.power_sensor = power_sensor

    @staticmethod
    def _calculate_solar_position(latitude: float, longitude: float, timestamp: datetime) -> Tuple[float, float]:
        altitude = get_altitude(latitude, longitude, timestamp)
        azimuth = get_azimuth(latitude, longitude, timestamp)
        return azimuth, altitude

    @staticmethod
    def _is_daytime(altitude: float) -> bool:
        return altitude > 0

    @staticmethod
    def _convert_to_servo(az_deg: float, alt_deg: float) -> Tuple[float, float]:
        if az_deg < 0:
            az_deg += 360
        servo_az = (az_deg - AZIMUTH_OFFSET) / 2 + 90
        servo_az = max(0, min(180, servo_az))
        servo_alt = max(0, min(90, alt_deg + ALTITUDE_OFFSET))
        return servo_az, servo_alt

    def _read_dht(self):
        if not adafruit_dht or not board:
            print("  ✗ DHT 라이브러리(board/adafruit_dht) 미설치")
            return
        try:
            sensor_cls = getattr(adafruit_dht, DHT_SENSOR_KIND, adafruit_dht.DHT11)
            pin = getattr(board, DHT_PIN_NAME)
            sensor = sensor_cls(pin)
            humidity = sensor.humidity
            temperature = sensor.temperature
            if humidity is not None and temperature is not None:
                print(f"  온도: {temperature:.1f}°C")
                print(f"  습도: {humidity:.1f}%")
            else:
                print("  ✗ DHT 측정 실패")
        except Exception as exc:
            print(f"  ✗ DHT 오류: {exc}")

    def _read_power(self):
        measurement = self.power_sensor.read()
        if not measurement:
            print("  ✗ INA219 읽기 실패 또는 초기화되지 않음")
            return
        v, a, w = measurement
        print(f"  전압: {v:.2f}V")
        print(f"  전류: {a:.3f}A")
        print(f"  전력: {w:.3f}W")

    def update(self) -> bool:
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
                return False

        az, alt = self._calculate_solar_position(latitude, longitude, timestamp)
        print(f"  태양 방위각: {az:.2f}°")
        print(f"  태양 고도각: {alt:.2f}°")

        if self._is_daytime(alt):
            print("  상태: 낮")
            servo_az, servo_alt = self._convert_to_servo(az, alt)
            self.servo.move_to_position(servo_az, servo_alt)
        else:
            print("  상태: 밤 → 초기 위치로 이동")
            self.servo.reset_position()

        print("\n[센서] 온습도 측정")
        self._read_dht()

        print("\n[센서] 전류/전압 측정")
        self._read_power()
        return True

    def run(self):
        print("\n╔═══════════════════════════════════════════════╗")
        print("║            🌞 태양 추적 시스템 시작            ║")
        print("╚═══════════════════════════════════════════════╝\n")

        self.servo.reset_position()
        time.sleep(2)
        try:
            while True:
                self.update()
                print(f"\n다음 업데이트까지 {UPDATE_INTERVAL}초 대기…")
                time.sleep(UPDATE_INTERVAL)
        finally:
            self.servo.cleanup()
            self.gps.close()


def create_tracker_from_env() -> SolarTracker:
    cache_mgr = CacheManager(CACHE_FILE)
    gps = GPSReader(GPS_PORT, GPS_BAUD, cache_mgr)
    gps.connect()
    gps.load_cached_position()
    servo = ServoController(SERVO_AZIMUTH_PIN, SERVO_ALTITUDE_PIN)
    power = PowerSensor(I2C_BUS_NUM)
    return SolarTracker(gps, servo, power)


if __name__ == "__main__":
    tracker = create_tracker_from_env()
    tracker.run()
