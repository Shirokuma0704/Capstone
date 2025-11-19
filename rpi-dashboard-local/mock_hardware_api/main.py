from flask import Flask, jsonify
import random
import psutil

app = Flask(__name__)

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
    motor_x_angle = random.randint(0, 180)
    motor_y_angle = random.randint(30, 150)
    
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

if __name__ == '__main__':
    # host='0.0.0.0'으로 설정하여 외부에서도 접근 가능하게 함
    app.run(host='0.0.0.0', port=5000, debug=True)
