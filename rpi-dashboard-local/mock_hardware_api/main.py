from flask import Flask, jsonify, request
import random
import psutil

app = Flask(__name__)

# 현재 모터 상태 저장 (시뮬레이션용)
current_motor_state = {
    "x_angle": 90,
    "y_angle": 90
}

@app.route('/api/v1/sensors', methods=['GET'])
def get_sensor_data():
    """
    실제 하드웨어 센서 값을 시뮬레이션하여 JSON으로 반환하는 API.
    하드웨어 담당자는 이 함수의 내용만 실제 센서 값으로 교체하면 됩니다.
    """
    
    # 1. 전력 데이터 시뮬레이션 (power_metrics)
    panel_voltage = round(random.uniform(4.5, 5.5), 2)
    panel_current = round(random.uniform(400.0, 600.0), 2)
    
    battery_voltage = round(random.uniform(3.7, 4.2), 2)
    # 배터리 전류: 양수면 충전, 음수면 방전
    battery_current = round(random.uniform(-200.0, 500.0), 2)

    # 2. 시스템 상태 데이터 시뮬레이션 (system_status)
    # 저장된 모터 상태 사용 (제어 명령 반영)
    motor_x_angle = current_motor_state["x_angle"]
    motor_y_angle = current_motor_state["y_angle"]
    
    temperature = round(random.uniform(20.0, 30.0), 1)
    humidity = round(random.uniform(40.0, 60.0), 1)
    
    # 포토다이오드 값 시뮬레이션 (빛이 특정 방향에 더 강하다고 가정)
    light_base = random.randint(300, 700)
    photo_left = light_base + random.randint(0, 50)
    photo_right = light_base - random.randint(0, 50)
    photo_up = light_base + random.randint(0, 50)
    photo_down = light_base - random.randint(0, 50)
    
    # 라즈베리파이 CPU 온도 (실제 값 또는 시뮬레이션)
    try:
        # psutil이 설치되어 있으면 실제 CPU 온도를 가져오려고 시도
        cpu_temp = psutil.sensors_temperatures()['cpu_thermal'][0].current
    except (AttributeError, KeyError, ImportError):
        # 실패 시 가상 값 사용
        cpu_temp = round(random.uniform(40.0, 55.0), 1)

    # 3. JSON 데이터 구조화
    data = {
        "power_metrics": {
            "solar_panel": {
                "voltage": panel_voltage,
                "current": panel_current,
                "power": round(panel_voltage * panel_current, 2)
            },
            "battery": {
                "voltage": battery_voltage,
                "current": battery_current
            }
        },
        "system_status": {
            "tracker": {
                "motor_x_angle": motor_x_angle,
                "motor_y_angle": motor_y_angle
            },
            "environment": {
                "temperature": temperature,
                "humidity": humidity
            },
            "light_sensors": {
                "up": photo_up,
                "down": photo_down,
                "left": photo_left,
                "right": photo_right
            },
            "controller": {
                "cpu_temp": cpu_temp
            }
        }
    }
    
    return jsonify(data)


@app.route('/api/v1/control/motor', methods=['POST'])
def control_motor():
    """
    모터 각도 제어 API
    실제 하드웨어 담당자는 이 함수에서 실제 모터를 제어하는 코드로 교체하면 됩니다.
    """
    try:
        data = request.get_json()

        # 요청 데이터 검증
        if not data:
            return jsonify({"error": "요청 데이터가 없습니다"}), 400

        x_angle = data.get('x_angle')
        y_angle = data.get('y_angle')

        # 값 검증
        if x_angle is None or y_angle is None:
            return jsonify({"error": "x_angle과 y_angle이 필요합니다"}), 400

        # 범위 검증
        if not (0 <= x_angle <= 180):
            return jsonify({"error": "x_angle은 0-180 사이여야 합니다"}), 400

        if not (30 <= y_angle <= 150):
            return jsonify({"error": "y_angle은 30-150 사이여야 합니다"}), 400

        # 모터 상태 업데이트 (시뮬레이션)
        current_motor_state["x_angle"] = int(x_angle)
        current_motor_state["y_angle"] = int(y_angle)

        # 실제 하드웨어 제어 코드는 여기에 추가
        # 예: servo_controller.set_angle(x_angle, y_angle)

        return jsonify({
            "status": "success",
            "message": "모터 제어 완료",
            "x_angle": current_motor_state["x_angle"],
            "y_angle": current_motor_state["y_angle"]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/control/status', methods=['GET'])
def get_control_status():
    """현재 모터 상태 조회"""
    return jsonify({
        "status": "success",
        "motor": current_motor_state
    })


if __name__ == '__main__':
    # host='0.0.0.0'으로 설정하여 외부에서도 접근 가능하게 함
    app.run(host='0.0.0.0', port=5000, debug=True)
