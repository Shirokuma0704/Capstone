"""하드웨어 API: 대시보드와 AI가 센서 조회 및 모터 제어에 접근하도록 제공"""

import os
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from Motor_GPS import (
    CacheManager,
    GPSReader,
    ServoController,
    NoOpServoController,
    SolarTracker,
    CACHE_FILE,
    GPS_PORT,
    GPS_BAUD,
    SERVO_AZIMUTH_PIN,
    SERVO_ALTITUDE_PIN,
    MANUAL_HOLD_SECONDS,
)

app = FastAPI(title="Solar Tracker Hardware API")

tracker: Optional[SolarTracker] = None
gps_reader: Optional[GPSReader] = None
servo: Optional[ServoController] = None


class MotorControlRequest(BaseModel):
    x_angle: int
    y_angle: int
    hold_seconds: int = MANUAL_HOLD_SECONDS


def _init_tracker():
    """GPS/서보 초기화 및 백그라운드 추적 시작"""
    global tracker, gps_reader, servo

    cache_mgr = CacheManager(CACHE_FILE)
    gps_reader = GPSReader(GPS_PORT, GPS_BAUD, cache_mgr)
    if not gps_reader.connect():
        print("⚠ GPS 연결 실패 (캐시/RTC 모드 대기)")
    gps_reader.load_cached_position()

    try:
        servo = ServoController(SERVO_AZIMUTH_PIN, SERVO_ALTITUDE_PIN)
    except Exception as e:
        print(f"⚠ 서보 초기화 실패, 더미 컨트롤러 사용: {e}")
        servo = NoOpServoController()

    tracker = SolarTracker(gps_reader, servo)
    tracker.start_background()


@app.on_event("startup")
async def startup_event():
    _init_tracker()


@app.get("/api/v1/sensors")
async def get_sensors():
    if tracker is None:
        raise HTTPException(status_code=503, detail="Tracker not ready")
    return tracker.get_latest_status()


@app.post("/api/v1/control/motor")
async def control_motor(request: MotorControlRequest):
    if tracker is None:
        raise HTTPException(status_code=503, detail="Tracker not ready")

    if not (0 <= request.x_angle <= 180):
        raise HTTPException(status_code=400, detail="x_angle은 0-180 사이여야 합니다")
    if not (0 <= request.y_angle <= 180):
        raise HTTPException(status_code=400, detail="y_angle은 0-180 사이여야 합니다")

    tracker.set_manual_position(
        request.x_angle, request.y_angle, hold_seconds=request.hold_seconds
    )
    return {
        "status": "success",
        "message": "모터 제어 완료 (수동 모드 유지)",
        "x_angle": request.x_angle,
        "y_angle": request.y_angle,
        "hold_seconds": request.hold_seconds,
    }


@app.post("/api/v1/control/auto/resume")
async def resume_auto():
    if tracker is None:
        raise HTTPException(status_code=503, detail="Tracker not ready")
    tracker.resume_auto()
    return {"status": "success", "message": "자동 추적 모드로 복귀했습니다."}


@app.get("/health")
async def health():
    return {"status": "ok", "tracker_ready": tracker is not None}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "hardware_api:app",
        host="0.0.0.0",
        port=int(os.getenv("HARDWARE_API_PORT", "5000")),
        reload=False,
    )
