# test_gps.py
import serial
import time
import pynmea2

# UART 설정 (GPIO 14/15 = /dev/serial0)
GPS_PORT = "/dev/serial0"
GPS_BAUD = 9600


def parse_gps_data(gps_serial):
    """GPS 데이터 파싱"""
    line = gps_serial.readline().decode('ascii', errors='replace').strip()

    if line.startswith('$GPRMC') or line.startswith('$GNRMC'):
        try:
            msg = pynmea2.parse(line)
            if msg.status == 'A':  # A = Active (유효한 데이터)
                print(f"\n=== GPS 위치 정보 ===")
                print(f"위도: {msg.latitude:.6f}°")
                print(f"경도: {msg.longitude:.6f}°")
                print(f"속도: {msg.spd_over_grnd if msg.spd_over_grnd else 0} knots")
                print(f"시간: {msg.timestamp}")
                print(f"날짜: {msg.datestamp}")
                return True
        except pynmea2.ParseError as e:
            pass

    return False


if __name__ == "__main__":
    print("=== NEO-6M GPS 모듈 테스트 ===")
    print("GPS 신호 수신 대기 중... (실외에서 테스트하세요)")

    try:
        gps = serial.Serial(GPS_PORT, GPS_BAUD, timeout=1)

        while True:
            if gps.in_waiting > 0:
                parse_gps_data(gps)
            time.sleep(0.1)

    except serial.SerialException as e:
        print(f"시리얼 포트 오류: {e}")
        print("\n해결 방법:")
        print("1. sudo raspi-config에서 Serial 활성화")
        print("2. /boot/config.txt에 dtoverlay=disable-bt 추가")
        print("3. sudo systemctl disable hciuart 실행")
    except KeyboardInterrupt:
        print("\n테스트 종료")
        gps.close()