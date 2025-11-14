# STGC 하드웨어 연결 가이드

## 목차
- [핀 배치도](#핀-배치도)
- [전원 구성](#전원-구성)
- [센서 연결](#센서-연결)
- [모터 연결](#모터-연결)
- [안전 회로](#안전-회로)
- [조립 가이드](#조립-가이드)

## 핀 배치도

### Raspberry Pi 4 GPIO 핀맵

```
     3V3  (1) (2)  5V
   GPIO2  (3) (4)  5V
   GPIO3  (5) (6)  GND
   GPIO4  (7) (8)  GPIO14
     GND  (9) (10) GPIO15
  GPIO17 (11) (12) GPIO18
  GPIO27 (13) (14) GND
  GPIO22 (15) (16) GPIO23
     3V3 (17) (18) GPIO24
  GPIO10 (19) (20) GND
   GPIO9 (21) (22) GPIO25
  GPIO11 (23) (24) GPIO8
     GND (25) (26) GPIO7
   GPIO0 (27) (28) GPIO1
   GPIO5 (29) (30) GND
   GPIO6 (31) (32) GPIO12
  GPIO13 (33) (34) GND
  GPIO19 (35) (36) GPIO16
  GPIO26 (37) (38) GPIO20
     GND (39) (40) GPIO21
```

### 핀 할당표

| 기능 | GPIO | 물리 핀 | 비고 |
|------|------|---------|------|
| **모터** |
| X축 서보 (MG996R) | GPIO18 | 12 | PWM0 |
| Y축 서보 (MG995) | GPIO13 | 33 | PWM1 |
| **센서** |
| DHT11 (온습도) | GPIO4 | 7 | 1-Wire |
| 포토다이오드 상단 | GPIO17 | 11 | ADC 필요 |
| 포토다이오드 하단 | GPIO27 | 13 | ADC 필요 |
| 포토다이오드 좌측 | GPIO22 | 15 | ADC 필요 |
| 포토다이오드 우측 | GPIO23 | 16 | ADC 필요 |
| **I2C 장치** |
| SDA | GPIO2 | 3 | I2C1 |
| SCL | GPIO3 | 5 | I2C1 |
| - INA219 (전류/전압) | 0x40 | I2C | |
| - DS3231 (RTC) | 0x68 | I2C | |
| **시리얼** |
| GPS RX | GPIO15 (TXD) | 10 | UART0 |
| GPS TX | GPIO14 (RXD) | 8 | UART0 |
| **전원** |
| 5V | - | 2, 4 | 서보모터 전원 |
| 3.3V | - | 1, 17 | 센서 전원 |
| GND | - | 6, 9, 14... | 공통 접지 |

## 전원 구성

### 전체 전원 구조

```
태양광 패널 (3W, ~6V)
    ↓
INA219 (전류/전압 측정)
    ↓
TP4056 (충전 컨트롤러)
    ↓
18650 배터리 (3.7V, 3500mAh)
    ↓
BMS (보호 회로)
    ↓
    ├─→ DC-DC 부스터 (3.7V → 5V) → Raspberry Pi 4
    └─→ DC-DC 부스터 (3.7V → 5V) → 서보모터 (별도 전원)
```

### 주의사항

⚠️ **전원 분리 중요!**
- **Raspberry Pi 전원**: 안정적인 5V/3A 공급 필요
- **서보모터 전원**: 별도 5V 라인 사용 (피크 전류 최대 2A)
- **센서 전원**: Raspberry Pi 3.3V 핀 사용 가능

⚠️ **공통 접지 필수!**
- 모든 장치의 GND는 반드시 연결

## 센서 연결

### 1. GPS 모듈 (NEO-6M)

```
GPS 모듈    Raspberry Pi
---------   -------------
VCC    →    3.3V (핀 1)
GND    →    GND (핀 6)
TX     →    GPIO15 (RXD, 핀 10)
RX     →    GPIO14 (TXD, 핀 8)
```

**설정:**
```bash
# UART 활성화
sudo raspi-config
# Interface Options > Serial Port
# Login shell: No
# Serial port hardware: Yes

# /boot/config.txt 수정
sudo nano /boot/config.txt
# 추가:
enable_uart=1
dtoverlay=disable-bt
```

### 2. INA219 (전류/전압 센서)

```
INA219      Raspberry Pi
---------   -------------
VCC    →    3.3V (핀 1)
GND    →    GND (핀 6)
SDA    →    GPIO2 (핀 3)
SCL    →    GPIO3 (핀 5)
VIN+   →    태양광 패널 (+)
VIN-   →    태양광 패널 (-)
```

**I2C 주소 설정:**
- A0, A1 핀 조합으로 주소 변경 가능
- 기본: 0x40 (A0=GND, A1=GND)
- 여러 개 사용 시 주소 분리 필요

### 3. DHT11 (온습도 센서)

```
DHT11       Raspberry Pi
---------   -------------
VCC    →    3.3V (핀 1)
GND    →    GND (핀 6)
DATA   →    GPIO4 (핀 7)
```

**회로:**
```
3.3V ─┬─ DHT11 VCC
      │
     [ ] 10kΩ 풀업 저항
      │
      └─ DHT11 DATA ─ GPIO4

GND  ─── DHT11 GND
```

### 4. 포토다이오드 (GL5528)

**ADC 모듈 필요!** Raspberry Pi는 아날로그 입력이 없으므로 MCP3008 ADC 사용

```
MCP3008     Raspberry Pi
---------   -------------
VDD    →    3.3V
VREF   →    3.3V
AGND   →    GND
DGND   →    GND
CLK    →    GPIO11 (SCLK, 핀 23)
DOUT   →    GPIO9 (MISO, 핀 21)
DIN    →    GPIO10 (MOSI, 핀 19)
CS     →    GPIO8 (CE0, 핀 24)

포토다이오드 연결:
CH0 ← 상단 센서
CH1 ← 하단 센서
CH2 ← 좌측 센서
CH3 ← 우측 센서
```

**포토다이오드 회로 (각 센서마다):**
```
3.3V ─┬─ GL5528 (포토다이오드)
      │
      ├─ MCP3008 CH0~3
      │
     [ ] 10kΩ 저항
      │
GND  ─┴─
```

### 5. DS3231 (RTC)

```
DS3231      Raspberry Pi
---------   -------------
VCC    →    3.3V (핀 1)
GND    →    GND (핀 6)
SDA    →    GPIO2 (핀 3)
SCL    →    GPIO3 (핀 5)
```

**설정:**
```bash
# RTC 활성화
sudo nano /boot/config.txt
# 추가:
dtoverlay=i2c-rtc,ds3231

# 시간 동기화
sudo hwclock -r
sudo hwclock -w
```

## 모터 연결

### 서보모터 연결

```
MG996R (X축)         MG995 (Y축)
--------------       --------------
갈색(GND)  → GND     갈색(GND)  → GND
적색(VCC)  → 5V      적색(VCC)  → 5V
주황(신호) → GPIO18  주황(신호) → GPIO13
```

**별도 전원 권장:**
```
                5V 전원 (서보모터용, 2A 이상)
                    │
        ┌───────────┴───────────┐
        │                       │
    MG996R VCC            MG995 VCC
    MG996R GND            MG995 GND
        │                       │
        └───────────┬───────────┘
                    │
              Raspberry Pi GND (공통 접지!)

    MG996R 신호 ← GPIO18 (PWM0)
    MG995 신호  ← GPIO13 (PWM1)
```

### PWM 설정

```python
import RPi.GPIO as GPIO

# 하드웨어 PWM 핀 사용 권장
X_AXIS_PIN = 18  # PWM0
Y_AXIS_PIN = 13  # PWM1

GPIO.setmode(GPIO.BCM)
GPIO.setup(X_AXIS_PIN, GPIO.OUT)
GPIO.setup(Y_AXIS_PIN, GPIO.OUT)

pwm_x = GPIO.PWM(X_AXIS_PIN, 50)  # 50Hz
pwm_y = GPIO.PWM(Y_AXIS_PIN, 50)

pwm_x.start(0)
pwm_y.start(0)

# 각도 변환 (0-180도 → 2-12% duty cycle)
def angle_to_duty(angle):
    return 2 + (angle / 18)
```

## 안전 회로

### 1차 보호: 퓨즈

```
태양광 패널 (+) ─── 퓨즈 (2A) ─── INA219 VIN+
```

### 2차 보호: MOSFET/릴레이

```
INA219 출력 ─── MOSFET/릴레이 ─── 배터리
                    │
                GPIO25 (제어 신호)
```

**과전류/과전압 차단 코드:**
```python
import RPi.GPIO as GPIO

RELAY_PIN = 25
GPIO.setup(RELAY_PIN, GPIO.OUT)

def emergency_shutdown():
    GPIO.output(RELAY_PIN, GPIO.LOW)  # 차단
    print("Emergency shutdown activated!")

# 전압/전류 모니터링
if voltage > 6.5 or current > 2.0:
    emergency_shutdown()
```

## 조립 가이드

### 1. 기계 구조

```
         [태양광 패널]
              │
         ┌────┴────┐
         │ Y축 서보 │ (상하 회전)
         └────┬────┘
              │
         ┌────┴────┐
         │ X축 서보 │ (좌우 회전)
         └────┬────┘
              │
         [고정 베이스]
```

### 2. 센서 배치

```
      [상단 포토다이오드]
            │
[좌측] ─ [패널] ─ [우측]
            │
      [하단 포토다이오드]
```

### 3. 배선 정리

- **색상 코드 사용 권장:**
  - 적색: 5V/3.3V 전원
  - 흑색: GND
  - 황색: 신호선
  - 청색: I2C (SDA)
  - 녹색: I2C (SCL)

- **케이블 타이 사용**: 움직이는 부분의 배선 고정

### 4. 최종 점검 체크리스트

- [ ] 모든 VCC/GND 연결 확인
- [ ] 공통 접지 연결 확인
- [ ] 서보모터 별도 전원 확인
- [ ] I2C 풀업 저항 확인 (보드에 내장된 경우 생략)
- [ ] 퓨즈 장착 확인
- [ ] 배선 단락 여부 멀티미터로 확인

## 회로도

자세한 회로도는 `/docs/schematics/` 디렉토리의 Fritzing 파일을 참조하세요.

## 문제 해결

### I2C 장치가 인식되지 않는 경우

```bash
# I2C 활성화 확인
sudo raspi-config
# Interface Options > I2C > Enable

# I2C 버스 스캔
sudo i2cdetect -y 1

# 연결 재확인: SDA, SCL, VCC, GND
```

### 서보모터가 떨리거나 작동하지 않는 경우

- 전원 용량 확인 (최소 2A)
- 별도 전원 사용
- 공통 접지 확인

### GPS 데이터 수신 안됨

- 안테나를 창가 또는 실외에 배치
- UART 설정 확인
- gpsd 상태 확인: `sudo systemctl status gpsd`

더 자세한 내용은 [TROUBLESHOOTING.md](TROUBLESHOOTING.md)를 참조하세요.
