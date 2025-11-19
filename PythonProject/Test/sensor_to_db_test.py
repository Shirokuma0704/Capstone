#!/usr/bin/env python3
"""
실제 센서 데이터를 읽어와서 InfluxDB에 저장하는 테스트 스크립트
- INA219: 전압/전류 센서
- DHT11: 온습도 센서
"""

import time
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
import os

# I2C 센서 (INA219)
try:
    import smbus2
    I2C_AVAILABLE = True
except ImportError:
    I2C_AVAILABLE = False
    print("⚠️  smbus2가 설치되어 있지 않습니다. I2C 센서를 사용할 수 없습니다.")

# DHT11 센서
try:
    import board
    import adafruit_dht
    DHT_AVAILABLE = True
except ImportError:
    DHT_AVAILABLE = False
    print("⚠️  adafruit_dht가 설치되어 있지 않습니다. DHT11 센서를 사용할 수 없습니다.")


# ==========================================
# InfluxDB 연결 설정
# ==========================================
INFLUX_URL = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
INFLUX_TOKEN = os.getenv('INFLUXDB_TOKEN', 'my-super-secret-token')
INFLUX_ORG = os.getenv('INFLUXDB_ORG', 'my-org')
INFLUX_BUCKET = os.getenv('INFLUXDB_BUCKET', 'my-bucket')

print(f"InfluxDB 연결: {INFLUX_URL}")
print(f"Organization: {INFLUX_ORG}")
print(f"Bucket: {INFLUX_BUCKET}")
print("=" * 60)


# ==========================================
# INA219 전압/전류 센서 클래스
# ==========================================
class INA219Sensor:
    def __init__(self, i2c_bus=3, addr=0x40):
        if not I2C_AVAILABLE:
            raise RuntimeError("smbus2가 설치되어 있지 않습니다.")

        self.bus = smbus2.SMBus(i2c_bus)
        self.addr = addr

        # 캘리브레이션 설정 (전류/전력 측정을 위해 필요)
        self._write_register(0x05, 4096)
        time.sleep(0.1)
        print(f"✅ INA219 센서 초기화 완료 (I2C Bus: {i2c_bus}, Addr: 0x{addr:02X})")

    def _write_register(self, reg, value):
        """16비트 레지스터에 쓰기 (Big-endian)"""
        val_swapped = ((value & 0xFF) << 8) | (value >> 8)
        self.bus.write_word_data(self.addr, reg, val_swapped)

    def _read_register(self, reg):
        """16비트 레지스터 읽기 (Big-endian)"""
        val = self.bus.read_word_data(self.addr, reg)
        val_swapped = ((val & 0xFF) << 8) | (val >> 8)
        return val_swapped

    def _get_signed_value(self, val):
        """16비트 부호 있는 정수 처리"""
        if val > 32767:
            val -= 65536
        return val

    def read_voltage(self):
        """배터리 전압 읽기 (V)"""
        raw = self._read_register(0x02)  # Bus Voltage 레지스터
        voltage = (raw >> 3) * 0.004  # 1 LSB = 4mV
        return voltage

    def read_shunt_voltage(self):
        """Shunt 전압 읽기 (mV) - 전류 계산에 사용"""
        raw = self._read_register(0x01)  # Shunt Voltage 레지스터
        signed_val = self._get_signed_value(raw)
        shunt_mv = signed_val * 0.01  # 1 LSB = 10μV
        return shunt_mv

    def read_current(self):
        """전류 읽기 (A) - Shunt 전압을 기반으로 계산"""
        shunt_mv = self.read_shunt_voltage()
        # 0.1 Ω Shunt 저항 사용 가정: I = V / R
        current_a = shunt_mv / 1000.0 / 0.1  # mV -> V, R = 0.1Ω
        return current_a

    def read_power(self):
        """전력 읽기 (W)"""
        voltage = self.read_voltage()
        current = self.read_current()
        power = voltage * current
        return power

    def get_data(self):
        """모든 센서 데이터 딕셔너리로 반환"""
        return {
            'voltage': round(self.read_voltage(), 3),
            'current': round(self.read_current(), 3),
            'power': round(self.read_power(), 3),
            'shunt_voltage_mv': round(self.read_shunt_voltage(), 3)
        }


# ==========================================
# DHT11 온습도 센서 클래스
# ==========================================
class DHT11Sensor:
    def __init__(self, gpio_pin=board.D17):
        if not DHT_AVAILABLE:
            raise RuntimeError("adafruit_dht가 설치되어 있지 않습니다.")

        self.dht_device = adafruit_dht.DHT11(gpio_pin)
        print(f"✅ DHT11 센서 초기화 완료 (GPIO: {gpio_pin})")

    def get_data(self):
        """온도와 습도 데이터 딕셔너리로 반환"""
        try:
            temperature = self.dht_device.temperature
            humidity = self.dht_device.humidity

            if temperature is not None and humidity is not None:
                return {
                    'temperature': float(temperature),
                    'humidity': float(humidity)
                }
            else:
                return None
        except RuntimeError as e:
            print(f"⚠️  DHT11 읽기 오류: {e.args[0]}")
            return None


# ==========================================
# InfluxDB에 데이터 저장
# ==========================================
def write_to_influxdb(client, write_api, data_points):
    """InfluxDB에 데이터 포인트 저장"""
    try:
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=data_points)
        print(f"✅ InfluxDB에 {len(data_points)}개 데이터 포인트 저장 완료")
        return True
    except Exception as e:
        print(f"❌ InfluxDB 저장 실패: {e}")
        return False


# ==========================================
# 메인 테스트 루프
# ==========================================
def main():
    print("\n🔬 센서 데이터 수집 및 InfluxDB 저장 테스트 시작")
    print("Ctrl+C로 종료\n")

    # InfluxDB 클라이언트 초기화
    try:
        client = influxdb_client.InfluxDBClient(
            url=INFLUX_URL,
            token=INFLUX_TOKEN,
            org=INFLUX_ORG
        )
        write_api = client.write_api(write_options=SYNCHRONOUS)
        print("✅ InfluxDB 클라이언트 연결 완료\n")
    except Exception as e:
        print(f"❌ InfluxDB 연결 실패: {e}")
        return

    # 센서 초기화
    sensors = {}

    if I2C_AVAILABLE:
        try:
            sensors['ina219'] = INA219Sensor(i2c_bus=3, addr=0x40)
        except Exception as e:
            print(f"❌ INA219 센서 초기화 실패: {e}")

    if DHT_AVAILABLE:
        try:
            sensors['dht11'] = DHT11Sensor(gpio_pin=board.D17)
        except Exception as e:
            print(f"❌ DHT11 센서 초기화 실패: {e}")

    if not sensors:
        print("⚠️  사용 가능한 센서가 없습니다. 테스트를 종료합니다.")
        return

    print("\n" + "=" * 60)
    print("📊 데이터 수집 시작 (5초마다)")
    print("=" * 60 + "\n")

    # 메인 루프
    try:
        while True:
            data_points = []
            timestamp = time.time()

            # INA219 전압/전류 데이터
            if 'ina219' in sensors:
                try:
                    ina_data = sensors['ina219'].get_data()
                    print(f"🔋 INA219: {ina_data}")

                    point = influxdb_client.Point("power_metrics") \
                        .tag("source", "solar_panel") \
                        .field("voltage", ina_data['voltage']) \
                        .field("current", ina_data['current']) \
                        .field("power", ina_data['power']) \
                        .time(int(timestamp * 1e9))
                    data_points.append(point)
                except Exception as e:
                    print(f"❌ INA219 읽기 오류: {e}")

            # DHT11 온습도 데이터
            if 'dht11' in sensors:
                try:
                    dht_data = sensors['dht11'].get_data()
                    if dht_data:
                        print(f"🌡️  DHT11: {dht_data}")

                        # 온도
                        point_temp = influxdb_client.Point("environment_sensors") \
                            .tag("type", "temperature") \
                            .field("value", dht_data['temperature']) \
                            .time(int(timestamp * 1e9))
                        data_points.append(point_temp)

                        # 습도
                        point_humid = influxdb_client.Point("environment_sensors") \
                            .tag("type", "humidity") \
                            .field("value", dht_data['humidity']) \
                            .time(int(timestamp * 1e9))
                        data_points.append(point_humid)
                except Exception as e:
                    print(f"❌ DHT11 읽기 오류: {e}")

            # InfluxDB에 저장
            if data_points:
                write_to_influxdb(client, write_api, data_points)
            else:
                print("⚠️  수집된 데이터가 없습니다.")

            print("-" * 60)
            time.sleep(5)

    except KeyboardInterrupt:
        print("\n\n테스트 종료")
    finally:
        client.close()
        print("InfluxDB 연결 종료")


if __name__ == "__main__":
    main()
