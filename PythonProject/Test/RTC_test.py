# test_ds3231.py
import smbus2
import time
from datetime import datetime

# I2C 버스 및 DS3231 주소
bus = smbus2.SMBus(1)
DS3231_ADDRESS = 0x68


def bcd_to_decimal(bcd):
    """BCD를 10진수로 변환"""
    return ((bcd >> 4) * 10) + (bcd & 0x0F)


def decimal_to_bcd(decimal):
    """10진수를 BCD로 변환"""
    return ((decimal // 10) << 4) | (decimal % 10)


def read_time():
    """DS3231에서 시간 읽기"""
    data = bus.read_i2c_block_data(DS3231_ADDRESS, 0x00, 7)

    second = bcd_to_decimal(data[0] & 0x7F)
    minute = bcd_to_decimal(data[1])
    hour = bcd_to_decimal(data[2] & 0x3F)
    day = bcd_to_decimal(data[4])
    month = bcd_to_decimal(data[5] & 0x1F)
    year = bcd_to_decimal(data[6]) + 2000

    return f"{year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"


def set_time():
    """현재 시스템 시간으로 DS3231 설정"""
    now = datetime.now()

    bus.write_byte_data(DS3231_ADDRESS, 0x00, decimal_to_bcd(now.second))
    bus.write_byte_data(DS3231_ADDRESS, 0x01, decimal_to_bcd(now.minute))
    bus.write_byte_data(DS3231_ADDRESS, 0x02, decimal_to_bcd(now.hour))
    bus.write_byte_data(DS3231_ADDRESS, 0x04, decimal_to_bcd(now.day))
    bus.write_byte_data(DS3231_ADDRESS, 0x05, decimal_to_bcd(now.month))
    bus.write_byte_data(DS3231_ADDRESS, 0x06, decimal_to_bcd(now.year - 2000))

    print(f"DS3231 시간 설정 완료: {now}")


if __name__ == "__main__":
    print("=== DS3231 RTC 테스트 ===")

    # 시간 설정 (처음 한 번만 실행)
    # set_time()

    # 시간 읽기 테스트
    for i in range(10):
        current_time = read_time()
        print(f"현재 시간: {current_time}")
        time.sleep(1)