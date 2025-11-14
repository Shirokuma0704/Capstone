# test_gps_connection.py
import serial
import time
import os

# UART 설정
GPS_PORT = "/dev/serial0"
GPS_BAUD = 9600


def check_serial_port():
    """시리얼 포트 존재 여부 확인"""
    print("=" * 60)
    print("1단계: 시리얼 포트 확인")
    print("=" * 60)

    if os.path.exists(GPS_PORT):
        print(f"✓ {GPS_PORT} 포트가 존재합니다.")
        return True
    else:
        print(f"✗ {GPS_PORT} 포트를 찾을 수 없습니다.")
        print("\n해결 방법:")
        print("  sudo raspi-config")
        print("  → Interface Options → Serial Port")
        print("  → 'login shell' NO, 'serial port hardware' YES")
        return False


def check_uart_config():
    """UART 설정 확인"""
    print("\n" + "=" * 60)
    print("2단계: UART 설정 확인")
    print("=" * 60)

    # /boot/config.txt 확인
    try:
        with open('/boot/config.txt', 'r') as f:
            config = f.read()

        if 'enable_uart=1' in config:
            print("✓ UART가 활성화되어 있습니다.")
        else:
            print("⚠ UART 활성화 설정이 없습니다.")
            print("  /boot/config.txt에 'enable_uart=1' 추가 권장")

        if 'dtoverlay=disable-bt' in config or 'dtoverlay=miniuart-bt' in config:
            print("✓ Bluetooth가 비활성화되어 있습니다 (GPIO 14/15 사용 가능)")
        else:
            print("⚠ Bluetooth 비활성화 설정이 없습니다.")
            print("  /boot/config.txt에 'dtoverlay=disable-bt' 추가 권장")

    except FileNotFoundError:
        print("⚠ /boot/config.txt 파일을 찾을 수 없습니다.")


def open_serial_connection():
    """시리얼 포트 열기"""
    print("\n" + "=" * 60)
    print("3단계: 시리얼 포트 열기")
    print("=" * 60)

    try:
        gps = serial.Serial(GPS_PORT, GPS_BAUD, timeout=2)
        print(f"✓ {GPS_PORT} 포트를 열었습니다.")
        print(f"  - Baud Rate: {GPS_BAUD}")
        print(f"  - Timeout: 2초")
        return gps
    except serial.SerialException as e:
        print(f"✗ 시리얼 포트를 열 수 없습니다: {e}")
        print("\n해결 방법:")
        print("  1. sudo usermod -a -G dialout $USER")
        print("  2. 로그아웃 후 다시 로그인")
        print("  3. sudo reboot")
        return None


def check_data_reception(gps, duration=10):
    """데이터 수신 확인"""
    print("\n" + "=" * 60)
    print(f"4단계: 데이터 수신 확인 ({duration}초간 대기)")
    print("=" * 60)
    print("GPS 모듈에서 데이터가 들어오는지 확인 중...\n")

    start_time = time.time()
    data_received = False
    line_count = 0
    nmea_types = set()

    while time.time() - start_time < duration:
        if gps.in_waiting > 0:
            try:
                line = gps.readline().decode('ascii', errors='replace').strip()

                if line.startswith('$'):
                    data_received = True
                    line_count += 1

                    # NMEA 문장 종류 추출
                    nmea_type = line.split(',')[0] if ',' in line else line
                    nmea_types.add(nmea_type)

                    # 처음 5줄만 출력
                    if line_count <= 5:
                        print(f"  수신: {line}")
                    elif line_count == 6:
                        print("  ... (계속 수신 중)")

            except Exception as e:
                print(f"⚠ 데이터 읽기 오류: {e}")

        time.sleep(0.1)

    print(f"\n결과:")
    if data_received:
        print(f"✓ 총 {line_count}개의 NMEA 문장을 수신했습니다.")
        print(f"✓ 수신된 NMEA 문장 종류: {', '.join(sorted(nmea_types))}")
        return True
    else:
        print("✗ 데이터를 수신하지 못했습니다.")
        print("\n확인 사항:")
        print("  1. GPS 모듈 전원 연결 확인 (3.3V 또는 5V)")
        print("  2. TX/RX 핀 연결 확인")
        print("     - GPS TX → 라즈베리파이 RX (GPIO 15, 10번 핀)")
        print("     - GPS RX → 라즈베리파이 TX (GPIO 14, 8번 핀)")
        print("  3. GPS 모듈의 LED가 깜빡이는지 확인")
        return False


def analyze_nmea_sentences(gps, duration=20):
    """NMEA 문장 분석"""
    print("\n" + "=" * 60)
    print(f"5단계: NMEA 문장 상세 분석 ({duration}초간)")
    print("=" * 60)
    print("GPS 위성 신호 수신 상태 확인 중...\n")

    start_time = time.time()
    sentence_stats = {}
    gps_fix_found = False
    satellites_visible = 0

    while time.time() - start_time < duration:
        if gps.in_waiting > 0:
            try:
                line = gps.readline().decode('ascii', errors='replace').strip()

                if line.startswith('$'):
                    parts = line.split(',')
                    sentence_type = parts[0]

                    # 통계 수집
                    sentence_stats[sentence_type] = sentence_stats.get(sentence_type, 0) + 1

                    # GPGGA - GPS Fix 정보
                    if sentence_type in ['$GPGGA', '$GNGGA'] and len(parts) > 7:
                        fix_quality = parts[6] if len(parts) > 6 else '0'
                        if fix_quality != '0' and fix_quality != '':
                            gps_fix_found = True
                            sats = parts[7] if len(parts) > 7 else '0'
                            try:
                                satellites_visible = int(sats)
                                print(f"✓ GPS Fix 획득! (위성 {satellites_visible}개 사용 중)")
                            except:
                                pass

                    # GPGSV - 가시 위성 정보
                    if sentence_type in ['$GPGSV', '$GNGSV'] and len(parts) > 3:
                        total_sats = parts[3] if len(parts) > 3 else '0'
                        try:
                            print(f"  → 가시 위성 수: {total_sats}개")
                        except:
                            pass

                    # GPRMC - 권장 최소 데이터
                    if sentence_type in ['$GPRMC', '$GNRMC'] and len(parts) > 2:
                        status = parts[2] if len(parts) > 2 else 'V'
                        if status == 'A':
                            print(f"✓ 유효한 위치 데이터 수신!")

            except Exception as e:
                pass

        time.sleep(0.1)

    # 결과 요약
    print("\n" + "=" * 60)
    print("수신된 NMEA 문장 통계:")
    print("=" * 60)
    for sentence_type, count in sorted(sentence_stats.items()):
        print(f"  {sentence_type}: {count}개")

    print("\n" + "=" * 60)
    print("최종 결과:")
    print("=" * 60)

    if gps_fix_found:
        print(f"✓ GPS Fix 성공! 위성 {satellites_visible}개로 위치 확인 가능")
        print("  → GPS 모듈이 정상적으로 작동하고 있습니다.")
    else:
        print("⚠ GPS Fix를 획득하지 못했습니다.")
        print("\n참고:")
        print("  - GPS는 실외에서 하늘이 보이는 곳에서 테스트해야 합니다.")
        print("  - 첫 Fix 획득까지 1~5분 정도 걸릴 수 있습니다 (Cold Start)")
        print("  - 건물 내부나 창문 근처에서는 신호를 잡기 어렵습니다.")


def print_summary():
    """최종 요약"""
    print("\n" + "=" * 60)
    print("NMEA 문장 설명:")
    print("=" * 60)
    print("  $GPGGA: GPS Fix 데이터 (위치, 고도, 위성 수)")
    print("  $GPGSA: 위성 정보 및 DOP (정확도)")
    print("  $GPGSV: 가시 위성 상세 정보")
    print("  $GPRMC: 권장 최소 데이터 (위치, 속도, 시간)")
    print("  $GPVTG: 속도 및 진행 방향")
    print("  $GPGLL: 위도/경도 정보")
    print("\n  GN으로 시작: GPS + GLONASS 혼합 수신")


if __name__ == "__main__":
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 15 + "GPS 모듈 연결 진단 도구" + " " * 18 + "║")
    print("╚" + "═" * 58 + "╝")
    print()

    try:
        # 1단계: 시리얼 포트 확인
        if not check_serial_port():
            print("\n❌ 테스트 중단: 시리얼 포트를 찾을 수 없습니다.")
            exit(1)

        # 2단계: UART 설정 확인
        check_uart_config()

        # 3단계: 시리얼 포트 열기
        gps = open_serial_connection()
        if gps is None:
            print("\n❌ 테스트 중단: 시리얼 포트를 열 수 없습니다.")
            exit(1)

        # 4단계: 데이터 수신 확인
        if not check_data_reception(gps, duration=10):
            print("\n❌ GPS 모듈에서 데이터를 받지 못했습니다.")
            print("   하드웨어 연결을 다시 확인해주세요.")
            gps.close()
            exit(1)

        # 5단계: NMEA 문장 분석
        analyze_nmea_sentences(gps, duration=20)

        # NMEA 문장 설명
        print_summary()

        # 연결 종료
        gps.close()

        print("\n" + "=" * 60)
        print("✓ GPS 연결 진단 완료!")
        print("=" * 60)
        print("\n다음 단계: test_gps.py를 실행하여 위치 정보를 확인하세요.")

    except KeyboardInterrupt:
        print("\n\n⚠ 사용자가 테스트를 중단했습니다.")
        try:
            gps.close()
        except:
            pass

    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
        import traceback

        traceback.print_exc()