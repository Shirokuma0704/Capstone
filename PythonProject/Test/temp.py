import time
import board
import adafruit_dht

# DHT11, GPIO4 (BCM 번호) 사용
dht_device = adafruit_dht.DHT11(board.D17)

def main():
    print("DHT11 온습도 센서 테스트 시작 (CTRL+C로 종료)")

    try:
        while True:
            try:
                temperature = dht_device.temperature  # 섭씨
                humidity = dht_device.humidity       # 상대습도 %

                if humidity is not None and temperature is not None:
                    print(f"온도: {temperature:.1f}°C, 습도: {humidity:.1f}%")
                else:
                    print("센서에서 데이터를 읽지 못했습니다.")
            except RuntimeError as e:
                # DHT 센서는 읽기 실패가 가끔 나는 게 정상이라 예외를 무시하고 다시 시도
                print(f"읽기 오류: {e.args[0]}")

            time.sleep(2)

    except KeyboardInterrupt:
        print("\n테스트 종료")

if __name__ == "__main__":
    main()