import json
from flask import Flask, jsonify, request
from dotenv import load_dotenv
import google.generativeai as genai
import re

# Import local modules
from . import config
from .db_analyzer import DBAnalyzer

# --- Initialization ---
load_dotenv()

# Initialize components
app = Flask(__name__)
db_analyzer = DBAnalyzer()
gemini_model = None


# --- Helper Functions ---

def _get_request_json():
    """Extracts JSON from request body, returns None if invalid."""
    body = request.get_json(silent=True)
    if body is None or not isinstance(body, dict):
        return None
    return body


def _get_gemini_model():
    """Initializes and returns the Gemini model client."""
    global gemini_model
    if gemini_model:
        return gemini_model
    if not config.gemini_config_ready():
        return None
    try:
        # NOTE: The API key is hardcoded here for simplicity in this context,
        # but it should be loaded from a secure source in production.
        genai.configure(api_key="AIzaSyAFRJTGN_yGPU2FvMiD-PkynWyngidz5sA")
        gemini_model = genai.GenerativeModel('gemini-1.5-flash-latest')
        return gemini_model
    except Exception as exc:
        print(f"Gemini initialization error: {exc}")
        return None

def _extract_period_from_command(command: str) -> str:
    """Extracts a time period (e.g., 24h, 7d) from the user command."""
    # "지난 7일", "last 7 days" -> "7d"
    match = re.search(r'(\d+)\s*(일|d)', command, re.IGNORECASE)
    if match:
        return f"-{match.group(1)}d"
    # "지난 24시간", "last 24 hours" -> "24h"
    match = re.search(r'(\d+)\s*(시간|h)', command, re.IGNORECASE)
    if match:
        return f"-{match.group(1)}h"
    return "-24h" # Default

def get_conversational_analysis(command: str):
    """
    Fetches DB summary and uses Gemini to generate a conversational analysis.
    """
    model = _get_gemini_model()
    if not model:
        return "AI 모델이 설정되지 않았습니다. GEMINI_API_KEY를 확인해주세요."

    # 1. Extract period and fetch data from DB
    period = _extract_period_from_command(command)
    summary_data = db_analyzer.get_summary(period)

    if not summary_data:
        return f"{period} 동안의 데이터가 없습니다. 다른 기간으로 조회해보세요."

    # 2. Create a new prompt for conversational analysis
    prompt = f"""
    당신은 태양광 발전 시스템의 데이터 분석 전문가입니다.
    사용자로부터 다음과 같은 데이터 요약을 받았습니다. 이 데이터를 바탕으로 사용자에게 친절하고 이해하기 쉬운 한국어 문장으로 분석 결과를 설명해주세요.
    데이터의 주요 특징(예: 최고/최저 발전량, 평균 효율 등)을 강조하고, 가능한 경우 인사이트를 제공해주세요.

    사용자 질문: "{command}"
    분석할 데이터 ({period} 기준):
    {json.dumps(summary_data, indent=2, ensure_ascii=False)}

    분석 예시:
    "지난 24시간 동안 평균 발전량은 55W였으며, 오후 1시경에 98W로 최고치를 기록했습니다. 평균 패널 효율은 15%로 양호한 수준을 보였습니다."

    이제 위 데이터를 바탕으로 사용자에게 응답을 생성해주세요.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as exc:
        return f"AI 분석 중 오류가 발생했습니다: {exc}"


# --- Conversational AI Endpoint ---

@app.route('/mcp/actions/naturalCommand', methods=['POST'])
def natural_command_action():
    """
    Handles natural language queries for data analysis.
    """
    json_input = _get_request_json()
    if json_input is None:
        return jsonify({"result": "error", "message": "Invalid or missing JSON body"}), 400
    
    command = json_input.get('command')
    if not command:
        return jsonify({"result": "error", "message": "Missing 'command' in request body"}), 400

    # Get conversational analysis from AI
    analysis_response = get_conversational_analysis(command)

    # In the new flow, the `control_ui` expects a specific format.
    # We will wrap our text response in that format.
    # The frontend expects a JSON with a "response" key.
    return jsonify({
        "response": analysis_response,
        "action": None
    })


if __name__ == '__main__':
    # To run this server:
    # 1. Make sure you have a .env file with your Influx settings.
    # 2. Run the rpi-dashboard-local environment with `docker-compose up -d` for InfluxDB.
    # 3. Run this script: `python -m src.mcp_server` from the `PythonProject` directory.
    app.run(host='0.0.0.0', port=5001, debug=True)
