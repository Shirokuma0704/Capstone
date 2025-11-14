# STGC 문제 해결 가이드

## 목차
- [하드웨어 문제](#하드웨어-문제)
- [센서 문제](#센서-문제)
- [모터 문제](#모터-문제)
- [소프트웨어 문제](#소프트웨어-문제)
- [네트워크 문제](#네트워크-문제)
- [전원 문제](#전원-문제)

## 하드웨어 문제

### Raspberry Pi가 부팅되지 않음

**증상:** LED가 켜지지 않거나 깜빡임

**해결 방법:**
1. **전원 확인**
   ```bash
   # 전원 어댑터: 5V 3A 이상 필요
   # microSD 카드가 제대로 삽입되었는지 확인
   ```

2. **SD 카드 재작성**
   ```bash
   # Raspberry Pi Imager로 OS 재설치
   # https://www.raspberrypi.org/software/
   ```

3. **상태 LED 확인**
   - 적색 LED (전원): 계속 켜짐 → 정상
   - 녹색 LED (활동): 깜빡임 → SD 카드 접근 중
   - 녹색 LED 꺼짐 → SD 카드 문제

### I2C 장치 인식 안됨

**증상:** `i2cdetect`에서 장치가 보이지 않음

**해결 방법:**
1. **I2C 활성화 확인**
   ```bash
   sudo raspi-config
   # Interface Options > I2C > Enable

   # 재부팅
   sudo reboot
   ```

2. **연결 확인**
   ```bash
   # I2C 버스 스캔
   sudo i2cdetect -y 1

   # 예상 주소:
   # INA219: 0x40
   # DS3231: 0x68
   ```

3. **배선 재확인**
   - SDA: GPIO2 (핀 3)
   - SCL: GPIO3 (핀 5)
   - VCC: 3.3V
   - GND: GND
   - 풀업 저항 확인 (대부분 모듈에 내장)

4. **전압 측정**
   ```bash
   # 멀티미터로 VCC 전압 확인
   # 3.3V ± 0.2V 범위 내여야 함
   ```

### 핀 손상 확인

```bash
# GPIO 핀 테스트
gpio readall

# 특정 핀 테스트
gpio -g mode 18 out
gpio -g write 18 1  # HIGH
gpio -g write 18 0  # LOW
```

## 센서 문제

### GPS 데이터 수신 안됨

**증상:** GPS 모듈에서 데이터를 받지 못함

**해결 방법:**
1. **UART 설정 확인**
   ```bash
   # /boot/config.txt 확인
   sudo nano /boot/config.txt

   # 다음 줄이 있어야 함:
   enable_uart=1
   dtoverlay=disable-bt

   # 재부팅
   sudo reboot
   ```

2. **시리얼 포트 확인**
   ```bash
   ls -l /dev/ttyAMA* /dev/ttyUSB*

   # GPS 연결 테스트
   cat /dev/ttyAMA0
   # NMEA 문장이 보여야 함: $GPGGA, $GPRMC 등
   ```

3. **gpsd 설정**
   ```bash
   # gpsd 설정 파일 확인
   sudo nano /etc/default/gpsd

   # 올바른 설정:
   DEVICES="/dev/ttyAMA0"
   GPSD_OPTIONS="-n"

   # gpsd 재시작
   sudo systemctl restart gpsd
   sudo systemctl status gpsd

   # GPS 상태 확인
   cgps -s
   # 또는
   gpsmon
   ```

4. **안테나 위치**
   - GPS 안테나를 창가 또는 실외에 배치
   - 첫 고정(Fix)까지 5-10분 소요 가능
   - 위성 수가 4개 이상이어야 정확한 위치 확인

5. **수동 테스트**
   ```python
   import serial

   gps = serial.Serial('/dev/ttyAMA0', 9600, timeout=1)

   while True:
       line = gps.readline().decode('utf-8', errors='ignore')
       print(line)
   ```

### INA219 전류/전압 센서 문제

**증상:** 전류/전압 값이 0 또는 비정상

**해결 방법:**
1. **I2C 주소 확인**
   ```bash
   sudo i2cdetect -y 1
   # 0x40에 보여야 함
   ```

2. **라이브러리 테스트**
   ```python
   from board import SCL, SDA
   import busio
   from adafruit_ina219 import INA219

   i2c = busio.I2C(SCL, SDA)
   ina = INA219(i2c)

   print(f"Voltage: {ina.bus_voltage}V")
   print(f"Current: {ina.current}mA")
   print(f"Power: {ina.power}mW")
   ```

3. **배선 확인**
   - VIN+/VIN-가 측정 대상에 올바르게 연결되었는지 확인
   - 극성 확인 (+ → +, - → -)

4. **캘리브레이션**
   ```python
   # 32V, 2A 범위로 재설정
   ina.bus_voltage_range = 1  # 32V
   ina.gain = 3               # 320mV
   ```

### DHT11 온습도 센서 오류

**증상:** `RuntimeError: DHT sensor not found` 또는 잘못된 값

**해결 방법:**
1. **라이브러리 재설치**
   ```bash
   sudo pip3 uninstall adafruit-circuitpython-dht
   sudo pip3 install adafruit-circuitpython-dht
   sudo apt-get install libgpiod2
   ```

2. **풀업 저항 확인**
   - DATA 핀과 VCC 사이에 10kΩ 저항 필요
   - 일부 모듈은 내장됨

3. **전원 확인**
   - 3.3V 또는 5V (모듈에 따라 다름)
   - 안정적인 전원 공급 필요

4. **코드 수정**
   ```python
   import time
   import board
   import adafruit_dht

   dht = adafruit_dht.DHT11(board.D4)

   for _ in range(5):  # 여러 번 시도
       try:
           temperature = dht.temperature
           humidity = dht.humidity
           print(f"Temp: {temperature}°C, Humidity: {humidity}%")
           break
       except RuntimeError as e:
           print(f"Error: {e}")
           time.sleep(2)
   ```

### 포토다이오드 값이 읽히지 않음

**증상:** ADC 값이 0 또는 최대값

**해결 방법:**
1. **MCP3008 ADC 연결 확인**
   ```bash
   # SPI 활성화
   sudo raspi-config
   # Interface Options > SPI > Enable
   ```

2. **SPI 테스트**
   ```python
   import spidev

   spi = spidev.SpiDev()
   spi.open(0, 0)  # Bus 0, Device 0
   spi.max_speed_hz = 1350000

   def read_adc(channel):
       if channel < 0 or channel > 7:
           return -1
       adc = spi.xfer2([1, (8 + channel) << 4, 0])
       data = ((adc[1] & 3) << 8) + adc[2]
       return data

   print(f"CH0: {read_adc(0)}")  # 0-1023
   ```

3. **저항 값 확인**
   - 분압 회로의 저항 값 확인 (10kΩ 권장)

## 모터 문제

### 서보모터가 작동하지 않음

**증상:** 모터가 움직이지 않거나 소음만 발생

**해결 방법:**
1. **전원 확인**
   ```bash
   # 서보모터는 많은 전류 필요 (각 1-2A)
   # Raspberry Pi GPIO 전원 사용 금지!
   # 별도 5V 전원 필수
   ```

2. **공통 접지 확인**
   - 서보모터 GND와 Raspberry Pi GND 연결 필수

3. **PWM 신호 테스트**
   ```python
   import RPi.GPIO as GPIO
   import time

   GPIO.setmode(GPIO.BCM)
   GPIO.setup(18, GPIO.OUT)

   pwm = GPIO.PWM(18, 50)  # 50Hz
   pwm.start(0)

   # 중립 위치 (90도)
   pwm.ChangeDutyCycle(7.5)
   time.sleep(1)

   # 0도
   pwm.ChangeDutyCycle(2.5)
   time.sleep(1)

   # 180도
   pwm.ChangeDutyCycle(12.5)
   time.sleep(1)

   pwm.stop()
   GPIO.cleanup()
   ```

4. **전원 용량 확인**
   ```bash
   # 5V 레귤레이터 용량: 최소 3A
   # 두 개 모터 동시 구동 시: 5A 권장
   ```

### 서보모터가 떨림

**해결 방법:**
1. **전원 필터링**
   - 전원 라인에 100μF 캐패시터 추가
   - 각 모터 근처에 설치

2. **코드 최적화**
   ```python
   # 부드러운 이동
   def move_servo_smooth(pwm, start_angle, end_angle, steps=20):
       for angle in range(start_angle, end_angle,
                         (end_angle - start_angle) // steps):
           duty = 2 + (angle / 18)
           pwm.ChangeDutyCycle(duty)
           time.sleep(0.05)
   ```

3. **하드웨어 PWM 사용**
   ```python
   # GPIO 18, 19 (PWM0, PWM1) 사용
   # 소프트웨어 PWM보다 안정적
   ```

## 소프트웨어 문제

### ModuleNotFoundError

**증상:** `ModuleNotFoundError: No module named 'xxx'`

**해결 방법:**
```bash
# 가상환경 사용 중인지 확인
which python3
which pip3

# 라이브러리 재설치
sudo pip3 install -r requirements.txt

# Python 버전 확인
python3 --version  # 3.7 이상 필요
```

### Permission denied (GPIO)

**증상:** `RuntimeError: No access to /dev/mem`

**해결 방법:**
```bash
# 사용자를 gpio 그룹에 추가
sudo usermod -a -G gpio $USER
sudo usermod -a -G i2c $USER
sudo usermod -a -G spi $USER

# 재로그인 필요
logout
# 또는
sudo reboot
```

### Python 스크립트 실행 오류

```bash
# 실행 권한 추가
chmod +x script.py

# shebang 추가 (파일 첫 줄)
#!/usr/bin/env python3

# 직접 실행
python3 script.py
```

### Flask 서버가 시작되지 않음

**해결 방법:**
```bash
# 포트 사용 확인
sudo netstat -tulpn | grep :5000

# 프로세스 종료
sudo kill -9 <PID>

# 다른 포트 사용
python3 mcp_server.py --port 8080
```

## 네트워크 문제

### SSH 연결 안됨

**해결 방법:**
1. **SSH 활성화**
   ```bash
   sudo raspi-config
   # Interface Options > SSH > Enable
   ```

2. **IP 주소 확인**
   ```bash
   hostname -I
   # 또는
   ip addr show
   ```

3. **방화벽 확인**
   ```bash
   sudo ufw status
   sudo ufw allow 22/tcp
   ```

### API 서버 접근 안됨

**해결 방법:**
```bash
# Flask가 모든 인터페이스에서 수신하는지 확인
app.run(host='0.0.0.0', port=5000)

# 방화벽 설정
sudo ufw allow 5000/tcp

# 네트워크 테스트
curl http://localhost:5000/mcp/info
```

## 전원 문제

### 배터리가 충전되지 않음

**증상:** 태양광 발전 중인데 배터리 충전 안됨

**해결 방법:**
1. **태양광 패널 출력 확인**
   ```bash
   # INA219로 전압 확인
   # 직사광선 아래: 5-6V
   # 흐린 날: 3-4V
   ```

2. **TP4056 상태 LED 확인**
   - 적색: 충전 중
   - 청색: 충전 완료
   - 꺼짐: 입력 전압 부족 또는 오류

3. **BMS 보호 회로 확인**
   - 과충전/과방전 보호 작동 여부
   - 배터리 전압: 3.0-4.2V 범위

4. **퓨즈 확인**
   - 멀티미터로 연속성 테스트

### 시스템이 랜덤하게 재부팅됨

**해결 방법:**
1. **전원 공급 확인**
   ```bash
   # 언더볼티지 확인
   vcgencmd get_throttled
   # 0x0: 정상
   # 0x50000: 언더볼티지 발생
   ```

2. **전원 어댑터 교체**
   - 5V 3A 이상 공식 어댑터 사용

3. **서보모터 전원 분리**
   - 서보모터와 라즈베리파이 전원 별도 공급

### 과전류/과전압 보호 작동

**증상:** 시스템이 자동으로 차단됨

**해결 방법:**
```python
# 보호 임계값 확인 및 조정
V_MAX = 6.5  # V
I_MAX = 2.0  # A

if voltage > V_MAX or current > I_MAX:
    # 릴레이 차단
    GPIO.output(RELAY_PIN, GPIO.LOW)
    log_error(f"Overload detected: V={voltage}, I={current}")
```

## 로그 확인

### 시스템 로그

```bash
# 부팅 로그
dmesg | tail -50

# 시스템 로그
journalctl -xe

# 특정 서비스 로그
sudo journalctl -u stgc.service -n 50
```

### 애플리케이션 로그

```python
# Python 로깅 설정
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/pi/Capstone/logs/app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.info("System started")
logger.error("Sensor error", exc_info=True)
```

## 성능 최적화

### CPU 온도 높음

```bash
# CPU 온도 확인
vcgencmd measure_temp

# 방열판 또는 팬 추가 권장
# 목표: 50°C 이하
```

### 메모리 부족

```bash
# 메모리 사용량 확인
free -h

# 스왑 파일 크기 증가
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# CONF_SWAPSIZE=2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

## 추가 지원

문제가 해결되지 않으면:
1. GitHub Issues: https://github.com/YOUR_USERNAME/Capstone/issues
2. 로그 파일 첨부
3. 시스템 정보 제공:
   ```bash
   cat /proc/cpuinfo
   uname -a
   python3 --version
   ```

## 참고 자료

- [Raspberry Pi Documentation](https://www.raspberrypi.org/documentation/)
- [RPi.GPIO Documentation](https://sourceforge.net/p/raspberry-gpio-python/wiki/Home/)
- [Adafruit CircuitPython](https://learn.adafruit.com/welcome-to-circuitpython)
