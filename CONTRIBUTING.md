# 기여 가이드

STGC 프로젝트에 기여해주셔서 감사합니다! 이 문서는 프로젝트 기여 방법을 안내합니다.

## 목차
- [개발 환경 설정](#개발-환경-설정)
- [코드 스타일](#코드-스타일)
- [커밋 메시지](#커밋-메시지)
- [Pull Request 프로세스](#pull-request-프로세스)
- [이슈 보고](#이슈-보고)

## 개발 환경 설정

### 1. 저장소 포크 및 클론

```bash
# 포크한 저장소 클론
git clone https://github.com/YOUR_USERNAME/Capstone.git
cd Capstone

# 원본 저장소를 upstream으로 추가
git remote add upstream https://github.com/ORIGINAL_OWNER/Capstone.git
```

### 2. 개발 브랜치 생성

```bash
# 최신 코드 가져오기
git fetch upstream
git checkout master
git merge upstream/master

# 새로운 기능 브랜치 생성
git checkout -b feature/your-feature-name
```

### 3. 의존성 설치

```bash
# Python 의존성 설치
pip3 install -r requirements.txt

# 개발 도구 설치 (선택사항)
pip3 install pytest black flake8 pylint
```

## 코드 스타일

### Python 코드 스타일

이 프로젝트는 [PEP 8](https://www.python.org/dev/peps/pep-0008/) 스타일 가이드를 따릅니다.

#### 기본 규칙

```python
# 들여쓰기: 스페이스 4개
def example_function(param1, param2):
    if param1 > param2:
        return param1
    return param2

# 한 줄 최대 길이: 79자
# 함수/클래스 사이: 빈 줄 2개
# 메서드 사이: 빈 줄 1개

# import 순서:
# 1. 표준 라이브러리
# 2. 서드파티 라이브러리
# 3. 로컬 모듈

import os
import sys

import RPi.GPIO as GPIO
from flask import Flask

from sensors.gps import GPSModule
```

#### 네이밍 컨벤션

```python
# 변수/함수: snake_case
variable_name = 10
def function_name():
    pass

# 클래스: PascalCase
class ClassName:
    pass

# 상수: UPPER_CASE
MAX_VOLTAGE = 6.5
I2C_ADDRESS = 0x40

# Private: _underscore_prefix
def _private_function():
    pass
```

#### Docstring

```python
def calculate_sun_position(latitude, longitude, timestamp):
    """
    GPS 좌표와 시간을 기반으로 태양 위치를 계산합니다.

    Args:
        latitude (float): 위도 (-90 ~ 90)
        longitude (float): 경도 (-180 ~ 180)
        timestamp (datetime): 계산 시점

    Returns:
        tuple: (azimuth, elevation) 각도 (도 단위)

    Raises:
        ValueError: 위도/경도 범위가 올바르지 않을 경우

    Example:
        >>> calculate_sun_position(35.1379, 129.0756, datetime.now())
        (180.5, 45.3)
    """
    pass
```

### 코드 포맷팅

```bash
# Black으로 자동 포맷팅
black PythonProject/

# Flake8로 스타일 검사
flake8 PythonProject/ --max-line-length=88

# Pylint로 정적 분석
pylint PythonProject/src/
```

### 테스트 작성

새로운 기능을 추가할 때는 테스트를 함께 작성해주세요.

```python
# tests/test_solar_calculation.py
import pytest
from tracking.solar import calculate_sun_position

def test_sun_position_calculation():
    """태양 위치 계산 테스트"""
    azimuth, elevation = calculate_sun_position(
        latitude=35.1379,
        longitude=129.0756,
        timestamp=datetime(2025, 6, 21, 12, 0, 0)
    )

    # 여름 정오 태양 고도는 약 80도
    assert 75 <= elevation <= 85
    # 방위각은 남쪽(180도) 근처
    assert 170 <= azimuth <= 190

def test_invalid_latitude():
    """잘못된 위도 입력 테스트"""
    with pytest.raises(ValueError):
        calculate_sun_position(
            latitude=100,  # 범위 초과
            longitude=129.0756,
            timestamp=datetime.now()
        )
```

```bash
# 테스트 실행
pytest tests/

# 커버리지 확인
pytest --cov=PythonProject tests/
```

## 커밋 메시지

### 커밋 메시지 형식

```
<type>: <subject>

<body>

<footer>
```

### Type 종류

- `feat`: 새로운 기능
- `fix`: 버그 수정
- `docs`: 문서 변경
- `style`: 코드 포맷팅, 세미콜론 누락 등
- `refactor`: 코드 리팩토링
- `test`: 테스트 추가/수정
- `chore`: 빌드 프로세스, 도구 설정 등

### 예시

```
feat: GPS 기반 태양 추적 알고리즘 추가

- SPA 알고리즘을 사용한 정밀 태양 위치 계산
- 위도/경도/시간 기반 방위각 및 고도 계산
- 단위 테스트 추가

Closes #42
```

```
fix: INA219 센서 오버플로우 문제 해결

전류가 높을 때 발생하는 오버플로우 문제 수정.
gain 설정을 조정하여 측정 범위 확대.

Fixes #15
```

## Pull Request 프로세스

### 1. 브랜치 업데이트

```bash
# upstream의 최신 변경사항 가져오기
git fetch upstream
git checkout master
git merge upstream/master

# 작업 브랜치에 rebase
git checkout feature/your-feature-name
git rebase master
```

### 2. 로컬 테스트

```bash
# 코드 스타일 검사
flake8 PythonProject/

# 테스트 실행
pytest tests/

# 실제 하드웨어 테스트 (가능한 경우)
python3 PythonProject/Test/GPS_Test.py
```

### 3. 커밋 푸시

```bash
git push origin feature/your-feature-name
```

### 4. Pull Request 생성

GitHub에서 Pull Request를 생성하고 다음 정보를 포함하세요:

#### PR 템플릿

```markdown
## 변경 사항
- 구현한 기능 또는 수정한 버그에 대한 설명

## 테스트
- [ ] 단위 테스트 작성 및 통과
- [ ] 통합 테스트 통과
- [ ] 하드웨어 테스트 완료 (해당하는 경우)

## 체크리스트
- [ ] 코드가 PEP 8 스타일 가이드를 따름
- [ ] Docstring 작성 완료
- [ ] 관련 문서 업데이트
- [ ] CHANGELOG.md 업데이트

## 관련 이슈
Closes #이슈번호
```

### 5. 코드 리뷰

- 리뷰어의 피드백에 적극적으로 대응해주세요
- 요청된 변경사항을 반영하고 커밋을 추가하세요
- 리뷰가 완료되면 프로젝트 관리자가 병합합니다

## 이슈 보고

### 버그 리포트

버그를 발견하면 GitHub Issues에 다음 정보와 함께 보고해주세요:

```markdown
## 버그 설명
간단한 버그 설명

## 재현 방법
1. ...
2. ...
3. ...

## 예상 동작
어떻게 동작해야 하는지

## 실제 동작
실제로 어떻게 동작하는지

## 환경
- Raspberry Pi 모델:
- OS 버전:
- Python 버전:
- 관련 라이브러리 버전:

## 추가 정보
로그, 스크린샷 등
```

### 기능 제안

새로운 기능을 제안할 때:

```markdown
## 기능 설명
제안하는 기능에 대한 간단한 설명

## 동기
왜 이 기능이 필요한지

## 구현 방안 (선택사항)
어떻게 구현할 수 있을지에 대한 아이디어

## 대안 (선택사항)
고려해본 다른 방법들
```

## 프로젝트 구조

새로운 모듈을 추가할 때는 다음 구조를 따라주세요:

```
PythonProject/
├── src/
│   ├── sensors/          # 센서 관련 모듈
│   │   ├── __init__.py
│   │   ├── gps.py
│   │   └── power.py
│   ├── motors/           # 모터 제어 모듈
│   ├── tracking/         # 추적 알고리즘
│   └── utils/            # 유틸리티
└── tests/                # 테스트 코드
    ├── test_sensors.py
    └── test_tracking.py
```

## 라이선스

이 프로젝트에 기여하는 모든 코드는 프로젝트의 라이선스를 따릅니다.

## 질문이나 도움이 필요한 경우

- GitHub Issues를 통해 질문하세요
- 팀원에게 직접 연락하세요

## 행동 강령

### 우리의 약속

모든 참여자에게 괴롭힘 없는 경험을 제공하기 위해 노력합니다.

### 기대하는 행동

- 친절하고 존중하는 언어 사용
- 다른 관점과 경험 존중
- 건설적인 비판 수용
- 커뮤니티에 가장 좋은 것에 집중

### 용납할 수 없는 행동

- 성적인 언어나 이미지 사용
- 트롤링, 모욕적인 코멘트, 개인 공격
- 괴롭힘 행위
- 타인의 개인 정보 공개

---

다시 한번 기여해주셔서 감사합니다! 🌞
