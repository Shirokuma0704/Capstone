# test_ina219_single.py
from ina219 import INA219
from ina219 import DeviceRangeError
import time

# INA219 설정
SHUNT_OHMS = 0.1
MAX_EXPECTED_AMPS = 3.2
INA219_ADDRESS = 0x40  # 기본 주소 (A0=GND, A1=GND)


def read_sensor(ina):
    """INA219 센서 데이터 읽기"""
    try:
        voltage = ina.voltage()
        current = ina.current()
        power = ina.power()

        print(f"전압: {voltage:.3f} V")
        print(f"전류: {current:.2f} mA")
        print(f"전력: {power:.2f} mW")

        return True

    except DeviceRangeError as e:
        print(f"측정 범위 초과: {e}")
        return False
    except Exception as e:
        print(f"읽기 오류: {e}")
        return False


if __name__ == "__main__":
    print("=== INA219 센서 테스트 (단일) ===\n")

    # INA219 센서 초기화
    try:
        ina = INA219(SHUNT_OHMS, MAX_EXPECTED_AMPS, address=INA219_ADDRESS)
        ina.configure(ina.RANGE_16V)
        print(f"✓ INA219 초기화 완료 (주소: {hex(INA219_ADDRESS)})\n")
    except Exception as e:
        print(f"✗ INA219 초기화 실패: {e}")
        print("\n확인 사항:")
        print("  1. I2C 연결 확인 (SDA, SCL, VCC, GND)")
        print("  2. I2C 주소 확인: sudo i2cdetect -y 1")
        print("  3. 라이브러리 설치: pip3 install pi-ina219")
        exit(1)

    # 데이터 읽기 테스트
    try:
        while True:
            print("=" * 40)
            print(f"측정 시각: {time.strftime('%H:%M:%S')}")
            print("-" * 40)

            read_sensor(ina)

            print()
            time.sleep(2)

    except KeyboardInterrupt:
        print("\n\n테스트 종료")