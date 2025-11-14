# STGC Python 프로젝트

이 디렉토리는 STGC 태양광 추적 시스템의 Python 제어 코드를 포함합니다.

## 📁 디렉토리 구조

```
PythonProject/
├── src/                    # 메인 소스 코드
│   ├── main.py            # 메인 실행 파일
│   ├── mcp_server.py      # MCP API 서버
│   ├── tracking/          # 태양 추적 모듈
│   ├── sensors/           # 센서 제어 모듈
│   ├── motors/            # 모터 제어 모듈
│   └── utils/             # 유틸리티 함수
├── Test/                   # 테스트 및 예제 코드
│   ├── GPS_Test.py        # GPS 테스트
│   ├── Volt_test.py       # 전압 센서 테스트
│   ├── RTC_test.py        # RTC 테스트
│   ├── Test.py            # 모터 테스트
│   ├── Test_solar_simple.py   # 단순 태양 추적
│   ├── Test_solar_advance.py  # 고급 태양 추적
│   └── sensor_motor.py    # 센서-모터 통합
├── config/                 # 설정 파일
│   ├── config.json        # 시스템 설정
│   └── config.example.json # 설정 예시
└── logs/                   # 로그 파일 디렉토리
    └── .gitkeep
```

## 🚀 빠른 시작

### 1. 의존성 설치

```bash
cd /home/user/Capstone
pip3 install -r requirements.txt
```

### 2. 설정 파일 구성

```bash
cd PythonProject/config
cp config.example.json config.json
nano config.json  # 환경에 맞게 수정
```

### 3. 하드웨어 테스트

개별 컴포넌트 테스트:

```bash
cd PythonProject/Test

# GPS 테스트
python3 GPS_Test.py

# 전압 센서 테스트
python3 Volt_test.py

# 모터 테스트
python3 Test.py
```

### 4. 메인 프로그램 실행

```bash
cd PythonProject/src
python3 main.py
```

### 5. MCP 서버 실행

```bash
cd PythonProject/src
python3 mcp_server.py

# 백그라운드 실행
nohup python3 mcp_server.py > ../logs/server.log 2>&1 &
```

## 📖 모듈 설명

### src/main.py
메인 제어 루프를 실행합니다. GPS 기반 태양 위치 계산, 포토다이오드 보정, 모터 제어를 통합합니다.

### src/mcp_server.py
Flask 기반 MCP API 서버입니다. 외부 클라이언트(AI, 모바일 앱 등)와 통신합니다.

### src/tracking/
태양 추적 알고리즘을 포함합니다:
- GPS 기반 태양 위치 계산
- 포토다이오드 보조 보정
- 날씨 판별 (흐린 날 대응)

### src/sensors/
센서 제어 모듈:
- `gps.py`: GPS 데이터 읽기
- `power.py`: INA219 전류/전압 측정
- `weather.py`: DHT11 온습도 센서
- `photodiode.py`: 포토다이오드 ADC 읽기
- `rtc.py`: DS3231 RTC

### src/motors/
서보모터 제어:
- PWM 신호 생성
- 각도 변환
- 부드러운 이동

### src/utils/
유틸리티 함수:
- 데이터 로깅
- 설정 파일 관리
- 시스템 상태 모니터링

## 🧪 테스트

### 단위 테스트

```bash
cd PythonProject
python3 -m pytest tests/
```

### 통합 테스트

```bash
# 센서-모터 통합
python3 Test/sensor_motor.py

# 태양 추적 시뮬레이션
python3 Test/Test_solar_advance.py
```

## 📊 데이터 로깅

로그 파일은 `logs/` 디렉토리에 저장됩니다:

- `power_log.csv`: 전력 데이터 (전압, 전류, 발전량)
- `position_log.csv`: 패널 위치 데이터
- `app.log`: 애플리케이션 로그

### CSV 형식

```csv
timestamp,voltage,current,power,battery_level
2025-11-14T12:00:00,5.12,0.58,2.97,85
```

## ⚙️ 설정

`config/config.json` 파일에서 시스템 설정을 변경할 수 있습니다:

```json
{
  "gps": {
    "port": "/dev/ttyAMA0",
    "baudrate": 9600
  },
  "motors": {
    "x_axis_pin": 18,
    "y_axis_pin": 13,
    "min_angle": 0,
    "max_angle": 180
  },
  "tracking": {
    "update_interval": 60,
    "correction_threshold": 5,
    "sleep_start": "19:00",
    "sleep_end": "06:00"
  }
}
```

## 🔒 안전 기능

- **과전류 보호**: 2A 이상 시 자동 차단
- **과전압 보호**: 6.5V 이상 시 자동 차단
- **온도 모니터링**: CPU 온도 80°C 이상 시 경고
- **야간 절전 모드**: 해가 진 후 자동 절전

## 📚 추가 문서

- [설치 가이드](../docs/SETUP.md)
- [하드웨어 연결](../docs/HARDWARE.md)
- [API 문서](../docs/API.md)
- [문제 해결](../docs/TROUBLESHOOTING.md)

## 🤝 기여

자세한 내용은 [CONTRIBUTING.md](../CONTRIBUTING.md)를 참조하세요.

## 📝 라이선스

이 프로젝트는 교육 목적의 캡스톤 디자인 프로젝트입니다.
