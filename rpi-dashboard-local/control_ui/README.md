# Solar Tracker Control Dashboard

태양광 트래커를 위한 통합 제어 대시보드입니다. AI 챗봇, 수동 제어, Grafana 모니터링을 하나의 웹 UI에서 제공합니다.

## 기능

### 1. AI 대화형 제어
- Claude AI를 통한 자연어 명령
- 예시: "패널을 정남향으로 조정해줘", "X축을 90도로 설정해줘"

### 2. 수동 제어
- 슬라이더를 통한 모터 각도 조정
- 프리셋 버튼 (중앙, 동쪽, 서쪽, 하늘)
- 실시간 센서 값 표시

### 3. Grafana 대시보드 임베딩
- 실시간 그래프 및 메트릭 표시
- 별도 탭 전환 없이 하나의 화면에서 모니터링

## 설정 방법

### 1. AI API 키 설정 (선택사항)

Claude AI 사용을 위해 환경 변수 설정:

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

또는 docker-compose.yml에 추가:

```yaml
control-ui:
  environment:
    - ANTHROPIC_API_KEY=your-api-key-here
```

### 2. 실행

```bash
cd rpi-dashboard-local
docker-compose up --build
```

### 3. 접속

- **통합 제어 대시보드**: http://localhost:8080
- Grafana (직접 접속): http://localhost:3000
- Hardware API: http://localhost:5000

## 사용 방법

### AI 챗봇 사용 예시

```
"X축을 90도, Y축을 60도로 설정해줘"
"패널을 동쪽으로 향하게 해줘"
"정남향으로 조정해줘"
"현재 각도는 어떻게 돼?"
```

### 수동 제어

1. 슬라이더로 원하는 각도 조정
2. "적용" 버튼 클릭
3. 또는 프리셋 버튼 클릭으로 즉시 적용

### Grafana 대시보드 설정

1. http://localhost:3000 접속
2. 대시보드 생성 (solar-tracker)
3. 통합 UI에서 자동으로 임베드됨

## API 엔드포인트

### 센서 데이터 조회
```
GET /api/sensors
```

### 모터 제어
```
POST /api/control/motor
{
  "x_angle": 90,
  "y_angle": 60
}
```

### AI 챗봇
```
POST /api/chat
{
  "message": "패널을 동쪽으로 향하게 해줘",
  "conversation_history": []
}
```

## 파일 구조

```
control_ui/
├── Dockerfile
├── requirements.txt
├── main.py              # FastAPI 백엔드
├── static/
│   ├── index.html       # 프론트엔드 UI
│   ├── style.css        # 스타일시트
│   └── app.js           # JavaScript
└── README.md
```

## 개발자 노트

### AI 없이 사용하기
ANTHROPIC_API_KEY를 설정하지 않으면 AI 기능 없이 수동 제어만 사용 가능합니다.

### 다른 AI API 사용하기
`main.py`의 `/api/chat` 엔드포인트를 수정하여 OpenAI, Gemini 등 다른 AI를 사용할 수 있습니다.

### 하드웨어 연동
`mock_hardware_api/main.py`의 `control_motor()` 함수에서 실제 모터 제어 코드를 추가하세요.
