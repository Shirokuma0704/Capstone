# STGC 설치 및 설정 가이드

## 목차
- [시스템 요구사항](#시스템-요구사항)
- [하드웨어 준비](#하드웨어-준비)
- [소프트웨어 설치](#소프트웨어-설치)
- [초기 설정](#초기-설정)
- [테스트 실행](#테스트-실행)

## 시스템 요구사항

### 하드웨어
- Raspberry Pi 4 (4GB RAM 권장)
- microSD 카드 (32GB 이상)
- 전원 어댑터 (5V 3A)
- 인터넷 연결 (초기 설정용)

### 소프트웨어
- Raspberry Pi OS (Bullseye 이상)
- Python 3.7 이상
- Git

## 하드웨어 준비

### 1. Raspberry Pi OS 설치

```bash
# Raspberry Pi Imager를 사용하여 OS 설치
# https://www.raspberrypi.org/software/

# SSH 활성화 (선택사항)
sudo raspi-config
# Interface Options > SSH > Enable
```

### 2. 하드웨어 연결

자세한 하드웨어 연결 방법은 [HARDWARE.md](HARDWARE.md)를 참조하세요.

## 소프트웨어 설치

### 1. 시스템 업데이트

```bash
sudo apt-get update
sudo apt-get upgrade -y
```

### 2. 필수 패키지 설치

```bash
# Python 및 개발 도구
sudo apt-get install -y python3 python3-pip python3-dev
sudo apt-get install -y git

# I2C 및 SPI 활성화
sudo raspi-config
# Interface Options > I2C > Enable
# Interface Options > SPI > Enable
```

### 3. GPIO 라이브러리 설치

```bash
# RPi.GPIO
sudo pip3 install RPi.GPIO

# 또는 lgpio (Raspberry Pi 5용)
sudo apt-get install -y python3-lgpio
```

### 4. 센서 라이브러리 설치

```bash
# INA219 (전류/전압 센서)
sudo pip3 install adafruit-circuitpython-ina219

# DHT11/DHT22 (온습도 센서)
sudo pip3 install adafruit-circuitpython-dht
sudo apt-get install -y libgpiod2

# GPS 라이브러리
sudo pip3 install gpsd-py3
sudo apt-get install -y gpsd gpsd-clients
```

### 5. 추가 라이브러리

```bash
# 데이터 처리
sudo pip3 install numpy pandas

# 웹 서버 (MCP 서버용)
sudo pip3 install flask flask-cors

# 시리얼 통신
sudo pip3 install pyserial

# RTC (실시간 시계)
sudo pip3 install smbus2
```

## 초기 설정

### 1. 프로젝트 클론

```bash
cd ~
git clone https://github.com/YOUR_USERNAME/Capstone.git
cd Capstone
```

### 2. 의존성 설치

```bash
pip3 install -r requirements.txt
```

### 3. GPS 설정

```bash
# GPS 시리얼 포트 확인
ls -l /dev/ttyAMA* /dev/ttyUSB*

# gpsd 설정
sudo nano /etc/default/gpsd
# DEVICES="/dev/ttyAMA0"  # 또는 /dev/ttyUSB0
# GPSD_OPTIONS="-n"

# gpsd 재시작
sudo systemctl restart gpsd
sudo systemctl enable gpsd
```

### 4. I2C 장치 확인

```bash
# I2C 버스 스캔
sudo i2cdetect -y 1

# 예상 주소:
# - INA219: 0x40, 0x41, 0x44, 0x45
# - DS3231: 0x68
```

### 5. 권한 설정

```bash
# GPIO 접근 권한
sudo usermod -a -G gpio $USER
sudo usermod -a -G i2c $USER
sudo usermod -a -G spi $USER

# 재로그인 필요
```

### 6. 설정 파일 구성

```bash
# config 디렉토리로 이동
cd PythonProject/config

# config.json 파일 생성 (예시)
cat > config.json << EOF
{
  "gps": {
    "port": "/dev/ttyAMA0",
    "baudrate": 9600
  },
  "motors": {
    "x_axis_pin": 18,
    "y_axis_pin": 13
  },
  "sensors": {
    "ina219_address": "0x40",
    "dht_pin": 4
  },
  "tracking": {
    "update_interval": 60,
    "correction_threshold": 5
  }
}
EOF
```

## 테스트 실행

### 1. 하드웨어 테스트

```bash
cd ~/Capstone/PythonProject/Test

# GPS 테스트
python3 GPS_Test.py

# 전압 센서 테스트
python3 Volt_test.py

# RTC 테스트
python3 RTC_test.py

# 모터 테스트
python3 Test.py
```

### 2. 태양 추적 테스트

```bash
# 단순 버전 (GPS 기반)
python3 Test_solar_simple.py

# 고급 버전 (GPS + 포토다이오드)
python3 Test_solar_advance.py

# 센서 + 모터 통합
python3 sensor_motor.py
```

### 3. MCP 서버 실행

```bash
cd ~/Capstone/PythonProject/src

# Flask 서버 시작
python3 mcp_server.py

# 또는 백그라운드 실행
nohup python3 mcp_server.py > server.log 2>&1 &
```

## 문제 해결

설치 중 문제가 발생하면 [TROUBLESHOOTING.md](TROUBLESHOOTING.md)를 참조하세요.

일반적인 문제:
- **GPIO 권한 오류**: 사용자를 gpio 그룹에 추가하고 재로그인
- **I2C 장치 인식 안됨**: I2C 활성화 확인 및 연결 재확인
- **GPS 데이터 수신 안됨**: 안테나 위치 및 gpsd 설정 확인

## 자동 시작 설정 (선택사항)

systemd 서비스로 자동 시작 설정:

```bash
sudo nano /etc/systemd/system/stgc.service
```

```ini
[Unit]
Description=STGC Solar Tracking System
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/Capstone/PythonProject/src
ExecStart=/usr/bin/python3 main.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 서비스 활성화
sudo systemctl daemon-reload
sudo systemctl enable stgc.service
sudo systemctl start stgc.service

# 상태 확인
sudo systemctl status stgc.service
```

## 다음 단계

- [API 문서](API.md) - MCP 서버 API 사용법
- [하드웨어 가이드](HARDWARE.md) - 하드웨어 연결 상세 가이드
- [문제 해결](TROUBLESHOOTING.md) - 일반적인 문제 해결 방법
