import json
import os
from flask import Flask, jsonify, request
from dotenv import load_dotenv
from google import genai
import re

# Import local modules
from . import config
from .db_analyzer import DBAnalyzer

# --- Initialization ---
load_dotenv()

# Initialize components
app = Flask(__name__)
db_analyzer = DBAnalyzer()
gemini_client = None


def _get_request_json():
    """Extracts JSON from request body, returns None if invalid."""
    body = request.get_json(silent=True)
    if body is None or not isinstance(body, dict):
        return None
    return body


def _get_gemini_client():
    """Initializes and returns the Gemini API client."""
    global gemini_client
    if gemini_client:
        return gemini_client

    # Get API key from environment
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Warning: GEMINI_API_KEY not found in environment")
        return None

    try:
        gemini_client = genai.Client(api_key=api_key)
        return gemini_client
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


def classify_intent(command: str, client):
    """
    Classifies whether the command requires data analysis or is general conversation.
    Returns: 'data_analysis' or 'general_conversation'
    """
    prompt = f"""
    사용자 입력을 분석하여 다음 중 하나로 분류하세요:
    1. "data_analysis" - 태양광 발전 데이터 조회/분석이 필요한 경우 (예: "지난 24시간 발전량", "어제 효율", "오늘 발전량")
    2. "general_conversation" - 일반적인 대화 (예: "안녕", "고마워", "어떻게 사용해?")

    사용자 입력: "{command}"

    오직 "data_analysis" 또는 "general_conversation" 중 하나만 답변하세요.
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        intent = response.text.strip().lower()
        if "data_analysis" in intent:
            return "data_analysis"
        return "general_conversation"
    except:
        return "general_conversation"


def get_conversational_analysis(command: str):
    """
    Fetches DB summary and uses Gemini to generate a conversational analysis.
    """
    client = _get_gemini_client()
    if not client:
        return "AI 모델이 설정되지 않았습니다. GEMINI_API_KEY를 확인해주세요."

    # 1. Classify user intent
    intent = classify_intent(command, client)

    # 2. Handle based on intent
    if intent == "general_conversation":
        # Just have a normal conversation
        prompt = f"""
        당신은 태양광 발전 시스템의 친절한 AI 어시스턴트입니다.
        사용자와 자연스럽게 대화하세요. 필요하면 시스템 사용법을 안내할 수 있습니다.

        사용자: "{command}"

        짧고 자연스럽게 한국어로 응답하세요.
        """
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            return response.text
        except Exception as exc:
            return f"응답 생성 중 오류가 발생했습니다: {exc}"

    # 3. Data analysis path (기존 코드)
    period = _extract_period_from_command(command)
    summary_data = db_analyzer.get_summary(period)

    if not summary_data:
        return f"{period} 동안의 데이터가 없습니다. 다른 기간으로 조회해보세요."

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
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text
    except Exception as exc:
        return f"AI 분석 중 오류가 발생했습니다: {exc}"


@app.route('/mcp/actions/naturalCommand', methods=['POST'])
def natural_command_action():
    """
    Handles natural language queries for data analysis or general conversation.
    """
    json_input = _get_request_json()
    if json_input is None:
        return jsonify({"result": "error", "message": "Invalid or missing JSON body"}), 400

    command = json_input.get('command')
    if not command or not command.strip():
        return jsonify({
            "result": "error",
            "message": "명령어를 입력해주세요."
        }), 400

    # Get response from AI (handles both conversation and analysis)
    analysis_response = get_conversational_analysis(command)

    return jsonify({
        "result": "success",
        "response": analysis_response,
        "action": "processed"
    })


if __name__ == '__main__':
    # To run this server:
    # 1. Make sure you have a .env file with your Influx settings.
    # 2. Run the rpi-dashboard-local environment with `docker-compose up -d` for InfluxDB.
    # 3. Run this script: `python -m src.mcp_server` from the `PythonProject` directory.
    app.run(host='0.0.0.0', port=5001, debug=True)
