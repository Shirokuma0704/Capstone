from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import httpx
import os
import json

app = FastAPI()

# 환경 변수
HARDWARE_API_URL = os.getenv("HARDWARE_API_URL", "http://host.docker.internal:5000")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://host.docker.internal:5001")

# Static 파일 서빙
app.mount("/static", StaticFiles(directory="static"), name="static")


# 요청 모델들
class MotorControlRequest(BaseModel):
    x_angle: int
    y_angle: int


class ChatRequest(BaseModel):
    message: str
    conversation_history: list = []


# 루트 엔드포인트
@app.get("/")
async def read_root():
    return FileResponse("static/index.html")


# 센서 데이터 조회 (Hardware API 프록시)
@app.get("/api/sensors")
async def get_sensors():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{HARDWARE_API_URL}/api/v1/sensors")
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hardware API 오류: {str(e)}")


# 모터 제어
@app.post("/api/control/motor")
async def control_motor(request: MotorControlRequest):
    """모터 각도 제어"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{HARDWARE_API_URL}/api/v1/control/motor",
                json={"x_angle": request.x_angle, "y_angle": request.y_angle}
            )
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"모터 제어 오류: {str(e)}")


# AI 챗봇 엔드포인트 (MCP 서버 프록시)
@app.post("/api/chat")
async def chat(request: ChatRequest):
    """사용자 메시지를 mcp_server로 전달하고 응답을 처리합니다."""
    try:
        async with httpx.AsyncClient() as client:
            # mcp_server의 naturalCommand 엔드포인트 호출
            response = await client.post(
                f"{MCP_SERVER_URL}/mcp/actions/naturalCommand",
                json={"command": request.message},
                timeout=30.0
            )
            response.raise_for_status()
            mcp_result = response.json()

            # mcp_server 응답을 UI가 이해하는 형식으로 변환
            interpreted_action = mcp_result.get("interpreted_action", {})
            action_type = interpreted_action.get("action")
            result_data = mcp_result.get("result", {})

            # 사용자에게 보여줄 응답 메시지 생성
            if action_type == "error":
                final_response = f"명령을 이해하지 못했습니다: {result_data.get('message', '알 수 없는 오류')}"
            elif result_data.get('status') == 'error':
                 final_response = f"명령 실행 중 오류가 발생했습니다: {result_data.get('message', '알 수 없는 오류')}"
            else:
                final_response = f"명령({request.message})이 해석되어 실행되었습니다.\n"
                final_response += f" - 해석된 동작: {action_type}\n"
                final_response += f" - 실행 결과: {json.dumps(result_data, ensure_ascii=False, indent=2)}"

            return {
                "response": final_response,
                "action": None  # 자동 실행은 mcp_server에서 처리하므로 여기서는 action을 보내지 않음
            }

    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"MCP 서버 연결 오류: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"챗봇 처리 중 오류 발생: {str(e)}")


# 헬스체크
@app.get("/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

