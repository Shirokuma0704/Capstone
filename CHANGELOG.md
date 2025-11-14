# Changelog

이 파일은 STGC 프로젝트의 모든 주요 변경사항을 기록합니다.

형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.0.0/)를 따르며,
이 프로젝트는 [Semantic Versioning](https://semver.org/lang/ko/)을 준수합니다.

## [Unreleased]

### 계획 중
- MPPT (Maximum Power Point Tracking) 알고리즘
- 배터리 관리 시스템(BMS) 고도화
- 클라우드 연동 (AWS IoT / Azure IoT Hub)
- 모바일 앱 개발
- WebSocket 실시간 스트리밍

## [1.0.0] - 2025-11-29

### Added
- 🎯 GPS 기반 2축 태양 추적 시스템
- 📊 실시간 전류/전압/발전량 모니터링
- 🤖 MCP (Model Context Protocol) API 서버
- 🌡️ 온습도 센서를 통한 날씨 판별
- 🔒 과전류/과전압 보호 회로
- 📝 데이터 로깅 및 CSV 저장
- 🌙 야간 자동 절전 모드
- ⚙️ JSON 기반 설정 관리

### 핵심 기능

#### 센서 모듈
- GPS 모듈 (NEO-6M) 통합
- INA219 전류/전압 센서
- DHT11 온습도 센서
- 포토다이오드 (GL5528) 4개 배치
- DS3231 RTC (실시간 시계)

#### 제어 시스템
- MG996R/MG995 서보모터 PWM 제어
- GPS 기반 태양 위치 계산 알고리즘
- 포토다이오드 보조 보정
- 부드러운 모터 이동

#### API 서버
- Flask 기반 RESTful API
- MCP 프로토콜 준수
- `/mcp/actions/getStatus` - 시스템 상태 조회
- `/mcp/actions/controlPanel` - 패널 각도 제어
- `/mcp/actions/setTrackingMode` - 추적 모드 변경
- `/mcp/actions/getPowerData` - 발전량 데이터 조회

#### 안전 기능
- 1차 보호: 퓨즈 (2A)
- 2차 보호: MOSFET/릴레이
- 자동 차단 시스템
- CPU 온도 모니터링

### Documentation
- 📖 README.md - 프로젝트 개요 및 시스템 구성
- 🔧 SETUP.md - 설치 및 설정 가이드
- ⚡ HARDWARE.md - 하드웨어 연결 가이드
- 📡 API.md - MCP 서버 API 문서
- 🛠️ TROUBLESHOOTING.md - 문제 해결 가이드
- 🤝 CONTRIBUTING.md - 기여 가이드

### Configuration
- JSON 기반 설정 시스템
- 예시 설정 파일 (config.example.json)
- 모듈별 독립 설정

### Testing
- GPS 테스트 (GPS_Test.py)
- 전압 센서 테스트 (Volt_test.py)
- RTC 테스트 (RTC_test.py)
- 모터 동작 테스트 (Test.py)
- 단순 태양 추적 (Test_solar_simple.py)
- 고급 태양 추적 (Test_solar_advance.py)
- 통합 테스트 (sensor_motor.py)

## [0.3.0] - 2025-11-15

### Added
- 포토다이오드 보조 보정 시스템
- MCP 서버 프로토타입
- 데이터 로깅 기능

### Changed
- 추적 알고리즘 정밀도 향상
- 전력 효율 최적화

### Fixed
- GPS 신호 끊김 문제 해결
- 서보모터 떨림 현상 개선

## [0.2.0] - 2025-11-01

### Added
- GPS 기반 태양 위치 계산
- INA219 전류/전압 모니터링
- RTC를 통한 시간 동기화

### Changed
- 하드웨어 구조 개선
- 배선 정리 및 케이블 타이 적용

### Fixed
- I2C 통신 오류 해결
- 전원 안정성 개선

## [0.1.0] - 2025-10-15

### Added
- 프로젝트 초기 설정
- 기본 서보모터 제어
- GPIO 핀 설정
- 센서 모듈 테스트 코드

### Hardware
- Raspberry Pi 4 기본 설정
- 서보모터 2개 (X축, Y축) 연결
- GPS 모듈 연결
- 전원 회로 구성

## [0.0.1] - 2025-09-19

### Added
- 프로젝트 기획
- 부품 목록 작성
- 아키텍처 설계
- 개발 일정 수립

---

## 변경 유형

- `Added`: 새로운 기능
- `Changed`: 기존 기능 변경
- `Deprecated`: 곧 제거될 기능
- `Removed`: 제거된 기능
- `Fixed`: 버그 수정
- `Security`: 보안 관련 변경

---

## 팀 정보

**동아대학교 전자공학과 캡스톤 디자인**

| 이름 | 역할 |
|------|------|
| 권형준 | 팀장, 하드웨어 제작 |
| 송승훈 | 문서 작업 |
| 백상철 | Python 개발 |
| 김덕현 | 통신 (Bluetooth, Wi-Fi) |
| 한태민 | 태양광 추적 메커니즘 |
| 김지훈 | 모터 제어, 앱 연결 |

**프로젝트 기간**: 2025.09.19 ~ 2025.11.29

---

[Unreleased]: https://github.com/YOUR_USERNAME/Capstone/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/YOUR_USERNAME/Capstone/compare/v0.3.0...v1.0.0
[0.3.0]: https://github.com/YOUR_USERNAME/Capstone/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/YOUR_USERNAME/Capstone/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/YOUR_USERNAME/Capstone/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/YOUR_USERNAME/Capstone/releases/tag/v0.0.1
