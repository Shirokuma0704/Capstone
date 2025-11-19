# STGC (Solar Tracking and Generation Control)
## 태양광 추적 발전 충전기

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Raspberry Pi](https://img.shields.io/badge/Platform-Raspberry%20Pi%204-red.svg)](https://www.raspberrypi.org/)
[![Python](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/)

## 📋 목차
- [프로젝트 개요](#-프로젝트-개요)
- [팀 정보](#-팀-정보)
- [연구 배경 및 목적](#-연구-배경-및-목적)
- [시스템 구성](#-시스템-구성)
- [하드웨어 설계](#-하드웨어-설계)
- [소프트웨어 설계](#-소프트웨어-설계)
- [로컬 개발 및 모니터링 환경](#-로컬-개발-및-모니터링-환경)
- [개발 일정](#-개발-일정)
- [기대효과](#-기대효과)
- [향후 확장](#-향후-확장)

## 🎯 프로젝트 개요

**개발 기간**: 2025년 9월 19일 ~ 2025년 11월 29일

STGC는 일반 가정용 소형·저비용 태양광 추적 발전 시스템입니다. 태양의 고도에 따라 자동으로 빛을 추적하여 에너지를 수집하며, 원격으로 충전량과 발전량을 확인할 수 있는 시스템입니다.

### 주요 특징
- 🌞 **2축 태양 추적**: GPS 기반 정밀 추적 + 포토다이오드 보조 보정
- 📊 **실시간 모니터링**: 전류/전압/발전량 측정 및 데이터 로깅
- 🤖 **AI 통합**: MCP(Model Context Protocol) 표준 준수
- ⚡ **전력 효율**: Raspberry Pi 4 + ESP32 분산 제어 구조
- 🔒 **안전 보호**: 이중 보호 회로 (퓨즈 + MOSFET/릴레이)

## 👥 팀 정보

| 이름 | 역할 | 담당 업무 |
|------|------|-----------|
| 권형준 | 팀장 | 하드웨어 제작, 배선, 회의록 작성 |
| 송승훈 | | 문서 작업, 과제 지정 |
| 백상철 | | 라즈베리파이 제어 흐름, Python 개발 |
| 김덕현 | | 통신 (Bluetooth, Wi-Fi) |
| 한태민 | | 태양광 추적 메커니즘, 부품 정리 |
| 김지훈 | | 모터 제어 코드, 앱 연결 |

**소속**: 동아대학교 공과대학 전자공학과

## 🌍 연구 배경 및 목적

### 배경
- 화석연료 고갈 및 온실가스 증가로 인한 기후변화 문제
- 원자력 발전의 안정성 및 폐기물 처리 한계
- 신재생에너지의 필요성 증대

### 목적
소형·저비용 태양광 추적 시스템을 개발하여 일반 가정에서도 효율적으로 태양광을 활용할 수 있도록 하는 것을 목표로 합니다. 개인의 재생에너지 사용 증가를 통해 전 세계적인 화석연료 감소 효과를 기대합니다.

## 🔧 시스템 구성

### 주요 부품

#### 1. 중앙 제어부
- **Raspberry Pi 4 (4GB)**: 센서 제어, 데이터 로깅, 웹서버
- **ESP32** (선택): 실시간 모터 제어 (전력 효율 향상)

#### 2. 태양광 발전부
- **태양광 패널**: 145×145mm, 3W
- **리튬이온 배터리**: 18650 (3500mAh)
- **BMS**: 배터리 관리 시스템
- **TP4056**: 충전 보조 회로

#### 3. 구동부
- **X축 (좌우)**: MG996R 고토크 서보모터
- **Y축 (상하)**: MG995 표준 서보모터
- **3D 프린팅 지지대**: U자형 브라켓 구조

#### 4. 센서부
| 센서 | 모델 | 용도 |
|------|------|------|
| GPS 모듈 | NEO-6M | 위치 기반 태양 추적 |
| 포토다이오드 | GL5528 | 미세 보정 (4개) |
| 온습도 센서 | DHT11 | 날씨 판별 |
| 전류/전압 센서 | INA219 | 발전량 측정 |
| RTC | DS3231 | 실시간 시계 |

#### 5. 안전 보호부
- **1차 보호**: 퓨즈 (과전류 차단)
- **2차 보호**: MOSFET/릴레이 (능동형 차단)

## 🔩 하드웨어 설계

### 기계 설계

#### 토크 계산
```
필요 토크 계산:
- 패널 질량: 0.2kg
- 필요 힘(F) = 0.2kg × 9.81m/s² ≈ 1.96 N
- 레버 암(L) = 145mm / 2 = 0.0725 m
- 최소 토크(T) = 1.96N × 0.0725m ≈ 0.14 N·m
- 안전계수 적용 (x3) = 0.42 N·m

선정된 모터:
- X축: MG996R (약 1 N·m) - 고토크
- Y축: MG995 (약 0.8 N·m) - 표준
```

### 회로 구성
```
태양광 패널 → INA219 → BMS → 리튬이온 배터리
                ↓
         라즈베리파이 4
                ↓
    ┌──────────┼──────────┐
    ↓          ↓          ↓
GPS 모듈   서보모터   포토다이오드
         (X, Y축)
```

## 💻 소프트웨어 설계

### 개발 환경

#### 필수 라이브러리
```bash
# 시스템 업데이트
sudo apt-get update
sudo apt-get install python3 python3-pip

# Python 라이브러리 설치
sudo pip3 install RPi.GPIO
sudo pip3 install adafruit-circuitpython-ina219
sudo pip3 install spidev
sudo pip3 install adafruit-circuitpython-dht
```

### 소프트웨어 아키텍처

#### 1. 핵심 제어 모듈

**센서 데이터 수집**
```python
# GPS 모듈
import serial
gps = serial.Serial('/dev/ttyAMA0', 9600)
line = gps.readline().decode('utf-8')

# 전류/전압 센서
from adafruit_ina219 import INA219
v = ina.bus_voltage
i = ina.current

# 온습도 센서
import adafruit_dht
temp = dht.temperature
hum = dht.humidity
```

**모터 제어**
```python
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setup(18, GPIO.OUT)
pwm = GPIO.PWM(18, 50)  # 50Hz
pwm.start(0)
pwm.ChangeDutyCycle(angle)
```

**추적 알고리즘**
```python
# GPS 기반 태양 위치 계산
# + 포토다이오드 보조 보정

error = left_sensor - right_sensor
if abs(error) > threshold:
    adjust_motor(error)
```

#### 2. 데이터 관리 모듈

**데이터 로깅**
```python
import csv
import time

with open("log.csv", "a", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([time.time(), v, i, power])
```

**보호 로직**
```python
# 과전압/과전류 감지 시 차단
if v > V_MAX or i > I_MAX:
    cut_off_relay()
```

#### 3. MCP 서버 모듈

Flask 기반 RESTful API 서버로 AI 클라이언트와 통신

```python
from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/mcp/actions/getStatus', methods=['POST'])
def get_status_action():
    status_data = core_logic.get_current_status()
    return jsonify({'result': status_data})

@app.route('/mcp/actions/controlPanel', methods=['POST'])
def control_panel_action():
    params = request.get_json().get('params', {})
    axis = params.get('axis')
    angle = params.get('angle')
    result = core_logic.set_panel_angle(axis, angle)
    return jsonify({'result': f"Panel {axis}-axis moved to {angle} degrees."})
```

## 📈 로컬 개발 및 모니터링 환경

본 프로젝트는 하드웨어 없이도 데이터 모니터링 및 대시보드 개발을 진행할 수 있도록 Docker 기반의 로컬 개발 환경을 제공합니다. `rpi-dashboard-local` 디렉터리에서 모든 작업을 수행합니다.

### 구성 요소
- **InfluxDB**: 시계열 데이터베이스. 모든 센서 데이터를 저장합니다.
- **Grafana**: 데이터 시각화 대시보드. InfluxDB의 데이터를 실시간으로 모니터링합니다.
- **Mock Hardware API**: 실제 하드웨어의 동작을 시뮬레이션하는 가상 API 서버.
- **Data Producer**: Mock API로부터 데이터를 받아 InfluxDB에 주기적으로 저장하는 스크립트.

### 사전 요구사항
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) 설치

### 실행 방법

1.  **터미널 1: InfluxDB & Grafana 실행**
    `rpi-dashboard-local` 디렉터리에서 아래 명령어를 실행하여 데이터베이스와 대시보드 서비스를 시작합니다.
    ```sh
    cd rpi-dashboard-local
    docker-compose up -d
    ```

2.  **터미널 2: Mock 하드웨어 API 서버 실행**
    새 터미널을 열고 `mock_hardware_api` 디렉터리에서 가상 센서 API 서버를 실행합니다.
    ```sh
    cd rpi-dashboard-local/mock_hardware_api
    pip install -r requirements.txt
    python main.py
    ```
    - 실행 후 웹 브라우저에서 `http://localhost:5000/api/v1/sensors` 주소로 접속하여 가상 데이터가 출력되는지 확인합니다.

3.  **터미널 3: 데이터 생산자 실행**
    또 다른 새 터미널을 열고 `data_producer` 디렉터리에서 데이터 수집 스크립트를 실행합니다.
    ```sh
    cd rpi-dashboard-local/data_producer
    pip install -r requirements.txt
    python write_data.py
    ```
    - "Successfully fetched and wrote..." 로그가 5초마다 출력되는지 확인합니다.

4.  **Grafana 대시보드 접속 및 설정**
    - 웹 브라우저에서 `http://localhost:3000` 으로 접속합니다. (초기 ID/PW: `admin`/`admin`)
    - 왼쪽 메뉴의 **Dashboards**로 이동하여 **Import** 버튼을 클릭합니다.
    - `rpi-dashboard-local/stgc_dashboard.json` 파일을 업로드합니다.
    - 데이터 소스를 **InfluxDB**로 선택하고 **Import**를 완료하면 실시간 모니터링 대시보드를 확인할 수 있습니다.

## 📅 개발 일정

### 소프트웨어 개발

| 주차 | 내용 |
|------|------|
| 1주차 | 아이디어 회의, 주제 확정, 전체 구조 구상 |
| 2주차 | 부품 선정 및 재료 구매 |
| 3주차 | 제어 환경 세팅 (Python GPIO, PWM 기본 코드) |
| 4주차 | 센서 입력 코드 구현 및 테스트 |
| 5주차 | 태양 위치 계산 알고리즘 구현 |
| 6주차 | 센서 + 모터 연동 테스트 |
| 7주차 | 보정 알고리즘 적용 |
| 8주차 | 데이터 로깅/그래프 기능 구현 |
| 9주차 | 통합 시연 프로그램 완성 |
| 10주차 | 최종 코드 정리 및 문서화 |

### 하드웨어 개발

| 주차 | 내용 |
|------|------|
| 1-2주차 | 부품 선정 및 구매 |
| 3주차 | 3D 모델링 시작 |
| 4주차 | 3D 프린터 출력 및 1차 조립 |
| 5주차 | HW 조립 보완 (센서 결선) |
| 6주차 | 전체 HW 통합조립 완료 |
| 7주차 | HW 안정화 (케이블 정리, 하우징) |
| 8주차 | 중간 발표 준비 |
| 9주차 | 최종점검 (내구성, 전원효율 테스트) |
| 10주차 | 최종 발표 자료 준비 |

## 🎯 기대효과

### 1. 발전 효율 향상
- 고정형 패널 대비 **20-30% 효율 증가** 기대
- GPS 기반 정밀 추적으로 날씨와 관계없이 이론적 최적 위치 추적

### 2. 데이터 기반 관리
- 실시간 발전량 모니터링
- CSV 데이터 로깅을 통한 효율 분석
- 시스템 상태 진단 및 장애 예측

### 3. 교육 및 연구 활용
- 소형·저비용 구조로 교육용/실험용 적합
- 임베디드 시스템 + 재생에너지 + AI 융합 연구 플랫폼

### 4. 환경 기여
- 가정용 재생에너지 사용 확대
- 화석연료 사용 감소 및 탄소 배출 저감

## 🚀 향후 확장

### 1. MPPT (Maximum Power Point Tracking)
```
현재: 단순 발전량 측정
향후: DC-DC 컨버터 연계 MPPT 알고리즘 적용
    - Perturb & Observe
    - Incremental Conductance
효과: 발전 효율 최대화 (일사량·온도 변화 대응)
```

### 2. 배터리 관리 시스템 (BMS) 고도화
- 리튬인산철(LiFePO₄) 배터리 적용
- 셀 밸런싱, 과충전/과방전 보호 강화
- 배터리 수명 연장 및 안전성 향상

### 3. IoT 및 AI 확장
- **클라우드 연동**: AWS IoT / Azure IoT Hub
- **AI 학습**: 발전 패턴 학습을 통한 예측 제어
- **모바일 앱**: 실시간 모니터링 및 원격 제어
- **스마트 그리드 연계**: 잉여 전력 판매

### 4. 응용 분야
- IoT 센서 노드 독립 전원
- 재난 상황 비상 전원
- 오프그리드 소형 발전 설비
- 교육용 키트 상용화

## 📊 부품 목록

| NO | 부품명 | 사양/모델명 | 수량 | 단가 |
|----|--------|------------|------|------|
| 1 | 라즈베리파이4 | 4GB | 1 | 86,000원 |
| 2 | 18650 리튬이온 배터리 | 3500mAh | 1 | 7,100원 |
| 3 | 태양광 패널 | 3W, 145×145mm | 1 | 38,900원 |
| 4 | GPS 모듈 | NEO-6M | 1 | 5,500원 |
| 5 | 온습도 센서 | DHT11 | 3 | 880원 |
| 6 | 포토다이오드 | GL5528 | 10 | 500원 |
| 7 | 서보모터1 | MG996R | 1 | 6,800원 |
| 8 | 서보모터2 | MG995 | 1 | 5,000원 |
| 9 | 전류전압 센서 | INA219 | 3 | 1,290원 |
| 10 | 충전 보조회로 | TP4056 | 4 | 1,000원 |
| 11 | 배터리 홀더 | 점퍼핀타입 | 3 | 390원 |
| 12 | 실시간 시계 | DS3231 | 1 | 8,500원 |
| 13 | 서보 암 | MAC-027 25T | 1 | 2,600원 |

## 📝 라이선스

이 프로젝트는 교육 목적의 캡스톤 디자인 프로젝트입니다.

## 📧 연락처

**동아대학교 전자공학과 캡스톤 디자인 팀**
- 프로젝트 기간: 2025.09.19 ~ 2025.11.29
- 지도: 동아대학교 전자공학과

---

### 참고 자료
- [Raspberry Pi Documentation](https://www.raspberrypi.org/documentation/)
- [Solar Position Algorithm](https://www.nrel.gov/grid/solar-resource/spa.html)
- [MCP Protocol Specification](https://spec.modelcontextprotocol.io/)

---

**Last Updated**: 2025.09.19
