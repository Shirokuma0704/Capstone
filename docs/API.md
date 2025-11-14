# STGC MCP 서버 API 문서

## 목차
- [개요](#개요)
- [MCP 프로토콜](#mcp-프로토콜)
- [API 엔드포인트](#api-엔드포인트)
- [데이터 모델](#데이터-모델)
- [에러 처리](#에러-처리)
- [사용 예시](#사용-예시)

## 개요

STGC MCP 서버는 Flask 기반 RESTful API를 제공하며, Model Context Protocol (MCP) 표준을 준수합니다.

**기본 URL:** `http://localhost:5000`

**프로토콜:** HTTP/HTTPS

**데이터 형식:** JSON

## MCP 프로토콜

### MCP 표준 엔드포인트

#### 1. 서버 정보 조회

```http
GET /mcp/info
```

**응답:**
```json
{
  "name": "STGC Solar Tracking System",
  "version": "1.0.0",
  "description": "Solar Tracking and Generation Control MCP Server",
  "capabilities": {
    "actions": true,
    "resources": true,
    "prompts": false
  },
  "server_info": {
    "platform": "Raspberry Pi 4",
    "python_version": "3.9.2"
  }
}
```

#### 2. 사용 가능한 액션 목록

```http
GET /mcp/actions
```

**응답:**
```json
{
  "actions": [
    {
      "name": "getStatus",
      "description": "현재 시스템 상태 조회",
      "input_schema": {
        "type": "object",
        "properties": {}
      }
    },
    {
      "name": "controlPanel",
      "description": "태양광 패널 각도 제어",
      "input_schema": {
        "type": "object",
        "properties": {
          "axis": {
            "type": "string",
            "enum": ["x", "y"],
            "description": "제어할 축 (x: 좌우, y: 상하)"
          },
          "angle": {
            "type": "number",
            "minimum": 0,
            "maximum": 180,
            "description": "목표 각도 (0-180도)"
          }
        },
        "required": ["axis", "angle"]
      }
    },
    {
      "name": "setTrackingMode",
      "description": "추적 모드 변경",
      "input_schema": {
        "type": "object",
        "properties": {
          "mode": {
            "type": "string",
            "enum": ["auto", "manual", "sleep"],
            "description": "추적 모드"
          }
        },
        "required": ["mode"]
      }
    },
    {
      "name": "getPowerData",
      "description": "발전량 데이터 조회",
      "input_schema": {
        "type": "object",
        "properties": {
          "period": {
            "type": "string",
            "enum": ["hour", "day", "week", "month"],
            "description": "조회 기간"
          }
        },
        "required": ["period"]
      }
    }
  ]
}
```

#### 3. 사용 가능한 리소스 목록

```http
GET /mcp/resources
```

**응답:**
```json
{
  "resources": [
    {
      "uri": "stgc://status",
      "name": "시스템 상태",
      "description": "실시간 시스템 상태 정보"
    },
    {
      "uri": "stgc://sensors/gps",
      "name": "GPS 데이터",
      "description": "현재 위치 정보"
    },
    {
      "uri": "stgc://sensors/power",
      "name": "전력 데이터",
      "description": "전류, 전압, 발전량"
    },
    {
      "uri": "stgc://logs",
      "name": "로그 데이터",
      "description": "시스템 로그"
    }
  ]
}
```

## API 엔드포인트

### 시스템 제어

#### 1. 시스템 상태 조회

```http
POST /mcp/actions/getStatus
```

**요청:**
```json
{
  "params": {}
}
```

**응답:**
```json
{
  "result": {
    "timestamp": "2025-11-14T12:30:00Z",
    "tracking_mode": "auto",
    "panel_position": {
      "x_axis": 45.5,
      "y_axis": 30.2
    },
    "sensors": {
      "gps": {
        "latitude": 35.1379,
        "longitude": 129.0756,
        "altitude": 10.5,
        "fix": true
      },
      "power": {
        "voltage": 5.12,
        "current": 0.58,
        "power": 2.97,
        "battery_level": 85
      },
      "weather": {
        "temperature": 23.5,
        "humidity": 65
      }
    },
    "sun_position": {
      "azimuth": 180.5,
      "elevation": 45.3
    },
    "system_health": {
      "cpu_temp": 45.2,
      "cpu_usage": 35.5,
      "memory_usage": 42.1,
      "uptime": 86400
    }
  }
}
```

#### 2. 패널 각도 제어

```http
POST /mcp/actions/controlPanel
```

**요청:**
```json
{
  "params": {
    "axis": "x",
    "angle": 90
  }
}
```

**응답:**
```json
{
  "result": {
    "success": true,
    "message": "Panel x-axis moved to 90 degrees",
    "current_position": {
      "x_axis": 90,
      "y_axis": 30.2
    }
  }
}
```

#### 3. 추적 모드 변경

```http
POST /mcp/actions/setTrackingMode
```

**요청:**
```json
{
  "params": {
    "mode": "auto"
  }
}
```

**응답:**
```json
{
  "result": {
    "success": true,
    "mode": "auto",
    "message": "Tracking mode changed to auto"
  }
}
```

**추적 모드:**
- `auto`: 자동 추적 (GPS + 포토다이오드)
- `manual`: 수동 제어 모드
- `sleep`: 절전 모드 (야간)

#### 4. 발전량 데이터 조회

```http
POST /mcp/actions/getPowerData
```

**요청:**
```json
{
  "params": {
    "period": "day"
  }
}
```

**응답:**
```json
{
  "result": {
    "period": "day",
    "start_time": "2025-11-14T00:00:00Z",
    "end_time": "2025-11-14T23:59:59Z",
    "total_energy": 15.8,
    "peak_power": 3.2,
    "average_power": 0.66,
    "data_points": [
      {
        "timestamp": "2025-11-14T06:00:00Z",
        "voltage": 4.95,
        "current": 0.12,
        "power": 0.59
      },
      {
        "timestamp": "2025-11-14T12:00:00Z",
        "voltage": 5.15,
        "current": 0.62,
        "power": 3.19
      }
    ]
  }
}
```

### 센서 데이터

#### 5. GPS 데이터 조회

```http
GET /mcp/resources/stgc://sensors/gps
```

**응답:**
```json
{
  "uri": "stgc://sensors/gps",
  "content": {
    "latitude": 35.1379,
    "longitude": 129.0756,
    "altitude": 10.5,
    "fix": true,
    "satellites": 8,
    "timestamp": "2025-11-14T12:30:00Z"
  }
}
```

#### 6. 전력 센서 데이터

```http
GET /mcp/resources/stgc://sensors/power
```

**응답:**
```json
{
  "uri": "stgc://sensors/power",
  "content": {
    "voltage": 5.12,
    "current": 0.58,
    "power": 2.97,
    "battery_voltage": 3.85,
    "battery_level": 85,
    "charging": true,
    "timestamp": "2025-11-14T12:30:00Z"
  }
}
```

#### 7. 날씨 센서 데이터

```http
GET /api/sensors/weather
```

**응답:**
```json
{
  "temperature": 23.5,
  "humidity": 65,
  "timestamp": "2025-11-14T12:30:00Z"
}
```

### 로그 및 분석

#### 8. 로그 데이터 조회

```http
GET /api/logs?limit=100&offset=0
```

**응답:**
```json
{
  "total": 1523,
  "limit": 100,
  "offset": 0,
  "logs": [
    {
      "timestamp": "2025-11-14T12:30:00Z",
      "level": "INFO",
      "module": "tracking",
      "message": "Panel adjusted to azimuth=180.5, elevation=45.3"
    },
    {
      "timestamp": "2025-11-14T12:29:50Z",
      "level": "DEBUG",
      "module": "sensor",
      "message": "Power reading: 2.97W"
    }
  ]
}
```

#### 9. 효율 분석

```http
GET /api/analysis/efficiency?period=week
```

**응답:**
```json
{
  "period": "week",
  "tracking_efficiency": 28.5,
  "comparison": {
    "with_tracking": 15.8,
    "without_tracking": 12.3,
    "improvement": 28.5
  },
  "optimal_angles": {
    "average_azimuth": 180,
    "average_elevation": 45
  }
}
```

## 데이터 모델

### Status

```typescript
interface Status {
  timestamp: string;           // ISO 8601 format
  tracking_mode: "auto" | "manual" | "sleep";
  panel_position: {
    x_axis: number;            // 0-180 degrees
    y_axis: number;            // 0-180 degrees
  };
  sensors: Sensors;
  sun_position: {
    azimuth: number;           // 0-360 degrees
    elevation: number;         // -90 to 90 degrees
  };
  system_health: SystemHealth;
}
```

### Sensors

```typescript
interface Sensors {
  gps: {
    latitude: number;
    longitude: number;
    altitude: number;
    fix: boolean;
  };
  power: {
    voltage: number;           // Volts
    current: number;           // Amperes
    power: number;             // Watts
    battery_level: number;     // 0-100 %
  };
  weather: {
    temperature: number;       // Celsius
    humidity: number;          // 0-100 %
  };
}
```

### SystemHealth

```typescript
interface SystemHealth {
  cpu_temp: number;            // Celsius
  cpu_usage: number;           // 0-100 %
  memory_usage: number;        // 0-100 %
  uptime: number;              // seconds
}
```

## 에러 처리

### 에러 응답 형식

```json
{
  "error": {
    "code": "INVALID_PARAMETER",
    "message": "Angle must be between 0 and 180",
    "details": {
      "parameter": "angle",
      "value": 200,
      "constraint": "0-180"
    }
  }
}
```

### 에러 코드

| 코드 | 설명 | HTTP 상태 |
|------|------|-----------|
| `INVALID_PARAMETER` | 잘못된 매개변수 | 400 |
| `SENSOR_ERROR` | 센서 읽기 오류 | 500 |
| `MOTOR_ERROR` | 모터 제어 오류 | 500 |
| `GPS_NO_FIX` | GPS 신호 없음 | 503 |
| `OVERLOAD` | 과전류/과전압 | 503 |
| `NOT_FOUND` | 리소스 없음 | 404 |
| `INTERNAL_ERROR` | 내부 서버 오류 | 500 |

## 사용 예시

### Python 클라이언트

```python
import requests
import json

BASE_URL = "http://192.168.1.100:5000"

# 시스템 상태 조회
response = requests.post(
    f"{BASE_URL}/mcp/actions/getStatus",
    json={"params": {}}
)
status = response.json()["result"]
print(f"Current power: {status['sensors']['power']['power']}W")

# 패널 각도 조절
response = requests.post(
    f"{BASE_URL}/mcp/actions/controlPanel",
    json={
        "params": {
            "axis": "x",
            "angle": 90
        }
    }
)
print(response.json()["result"]["message"])

# 발전량 데이터 조회
response = requests.post(
    f"{BASE_URL}/mcp/actions/getPowerData",
    json={
        "params": {
            "period": "day"
        }
    }
)
power_data = response.json()["result"]
print(f"Total energy today: {power_data['total_energy']}Wh")
```

### JavaScript/Node.js 클라이언트

```javascript
const axios = require('axios');

const BASE_URL = 'http://192.168.1.100:5000';

// 시스템 상태 조회
async function getStatus() {
  const response = await axios.post(`${BASE_URL}/mcp/actions/getStatus`, {
    params: {}
  });
  return response.data.result;
}

// 추적 모드 변경
async function setTrackingMode(mode) {
  const response = await axios.post(`${BASE_URL}/mcp/actions/setTrackingMode`, {
    params: { mode }
  });
  return response.data.result;
}

// 사용 예시
(async () => {
  const status = await getStatus();
  console.log(`Current power: ${status.sensors.power.power}W`);

  await setTrackingMode('auto');
  console.log('Tracking mode set to auto');
})();
```

### curl 예시

```bash
# 시스템 상태 조회
curl -X POST http://localhost:5000/mcp/actions/getStatus \
  -H "Content-Type: application/json" \
  -d '{"params": {}}'

# 패널 각도 제어
curl -X POST http://localhost:5000/mcp/actions/controlPanel \
  -H "Content-Type: application/json" \
  -d '{"params": {"axis": "x", "angle": 90}}'

# GPS 데이터 조회
curl -X GET http://localhost:5000/mcp/resources/stgc://sensors/gps
```

## WebSocket 실시간 스트리밍 (선택사항)

실시간 데이터 스트리밍을 위한 WebSocket 엔드포인트:

```javascript
const ws = new WebSocket('ws://localhost:5000/ws/stream');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Power:', data.power);
  console.log('Position:', data.position);
};

ws.send(JSON.stringify({
  subscribe: ['power', 'position', 'sensors']
}));
```

## 보안

### 인증 (향후 구현)

```http
Authorization: Bearer <token>
```

### HTTPS 설정

프로덕션 환경에서는 HTTPS 사용 권장:

```bash
# SSL 인증서 생성
openssl req -x509 -newkey rsa:4096 -nodes \
  -out cert.pem -keyout key.pem -days 365

# Flask 서버 실행
python3 mcp_server.py --ssl --cert cert.pem --key key.pem
```

## 참고 자료

- [MCP Protocol Specification](https://spec.modelcontextprotocol.io/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [RESTful API Design Best Practices](https://restfulapi.net/)
