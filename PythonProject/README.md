# STGC Python 프로젝트

이 디렉토리는 STGC 태양광 추적 시스템의 Python 제어 코드를 포함합니다.

## 📁 디렉토리 구조 (실제)

```
PythonProject/
├── src/                    # 메인 소스 코드
│   ├── __init__.py         # 패키지 초기화
│   ├── config.py           # 환경변수 기반 설정 로더
│   ├── db_analyzer.py      # InfluxDB 통계 조회
│   ├── sensor_reader.py    # GPS/INA219/DHT 센서 읽기(포토다이오드 제외)
│   ├── data_logger.py      # 센서 값을 InfluxDB에 기록
│   ├── hardware_control.py # 모터/센서 가상 제어 모듈
│   └── mcp_server.py       # Flask 기반 MCP 서버
├── config/                 # 설정 예시
│   └── config.example.json
├── logs/                   # 로그 파일 디렉토리
│   └── .gitkeep
├── Test/                   # 하드웨어/센서 실험 스크립트
└── requirements.txt
```

## 🚀 빠른 시작

### 1. 의존성 설치

```bash
cd /home/user/PycharmProjects/PythonProject
pip3 install -r requirements.txt
```

### 2. 환경변수 설정 (.env)

`PythonProject/.env` 파일을 만들고 아래 값을 채워주세요.

```
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your-token
INFLUXDB_ORG=your-org
INFLUXDB_BUCKET=your-bucket
GEMINI_API_KEY=your-gemini-key
```

*InfluxDB 관련 값이 비어 있어도 서버는 기동되지만 DB 관련 API는 사용할 수 없습니다. Gemini 키가 없으면 자연어 API는 비활성화됩니다.*

### 3. MCP 서버 실행

```bash
cd /home/user/PycharmProjects/PythonProject
python -m src.mcp_server

# 백그라운드 실행 예시
nohup python -m src.mcp_server > logs/server.log 2>&1 &
```

### 4. API 엔드포인트

- `POST /mcp/actions/getStatus`
- `POST /mcp/actions/controlPanel` (`params.axis`, `params.angle`)
- `POST /mcp/actions/getDbAnalysis` (`params.period` 예: `24h`, `-24h`, `7d`)
- `POST /mcp/actions/naturalCommand` (`command` 문자열; Gemini 필요)

## 📖 모듈 설명

- `src/config.py`: `.env`/환경변수에서 InfluxDB·Gemini 설정을 로드합니다.
- `src/db_analyzer.py`: 기간 요약 쿼리를 수행합니다. 기간 문자열은 자동으로 Flux 상대 시간(`-24h` 등)으로 정규화됩니다.
- `src/sensor_reader.py`: GPS/INA219/DHT 센서를 읽습니다. 포토다이오드는 제외됩니다. 하드웨어가 없으면 모의값으로 대체됩니다 (`USE_SENSOR_MOCK=1`).
- `src/data_logger.py`: `sensor_reader`로 읽은 값을 InfluxDB `sensor_data` 측정값으로 기록합니다.
- `src/hardware_control.py`: RPi.GPIO 없이 동작하는 가상 하드웨어 제어/센서 응답을 제공합니다.
- `src/mcp_server.py`: Flask MCP 서버. 요청 검증, 자연어 명령 처리(Gemini), DB 요약 제공 등을 담당합니다.

### 5. 센서 데이터 로거 실행 (포토다이오드 제외)

센서값을 InfluxDB에 주기적으로 기록합니다. 하드웨어가 없는 개발 환경에서는 `USE_SENSOR_MOCK=1`로 모의 데이터를 쓸 수 있습니다.

```bash
# 실제 센서 사용 (GPS: /dev/ttyAMA0, DHT11: board.D17, INA219: I2C)
python -m src.data_logger

# 모의 데이터로 테스트
USE_SENSOR_MOCK=1 LOG_INTERVAL=5 python -m src.data_logger
```

환경 변수
- `LOG_INTERVAL` (기본 10초)
- `MEASUREMENT_NAME` (기본 `sensor_data`)
- `GPS_PORT`(기본 `/dev/ttyAMA0`), `GPS_BAUD`(기본 9600)
- `DHT_PIN` (기본 `D17`)
- `USE_SENSOR_MOCK=1` → 센서 없이 동작

## 🧪 테스트/실험

실제 하드웨어 실험 스크립트는 `Test/` 디렉토리에 있습니다 (`GPS_Test.py`, `Volt_test.py` 등). 필요 시 개별 파일을 직접 실행하세요.

## ⚙️ 설정 예시 파일

`config/config.example.json`은 하드웨어/트래킹 설정 예시이며, 현재 서버 동작에는 필수는 아닙니다.

## 📝 라이선스

이 프로젝트는 교육 목적의 캡스톤 디자인 프로젝트입니다.
