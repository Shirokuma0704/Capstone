// 전역 변수
let conversationHistory = [];

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', () => {
    checkConnection();
    startSensorPolling();

    // Grafana iframe 로드 이벤트
    const iframe = document.getElementById('grafana-iframe');
    const placeholder = document.getElementById('grafana-placeholder');

    if (iframe && placeholder) {
        iframe.addEventListener('load', () => {
            // Fading out placeholder
            placeholder.classList.add('fade-out');
            
            // remove from DOM after animation
            setTimeout(() => {
                placeholder.style.display = 'none';
            }, 500); 
        });
    }
});

// 연결 상태 확인
async function checkConnection() {
    const statusElement = document.getElementById('connection-status');
    try {
        const response = await fetch('/health');
        if (response.ok) {
            const data = await response.json();
            statusElement.textContent = data.ai_enabled ? '✓ AI 연결됨' : '✓ 연결됨 (AI 비활성)';
            statusElement.classList.remove('disconnected');
        } else {
            throw new Error('연결 실패');
        }
    } catch (error) {
        statusElement.textContent = '✗ 연결 끊김';
        statusElement.classList.add('disconnected');
    }
}

// 센서 데이터 주기적으로 가져오기
function startSensorPolling() {
    updateSensorData();
    setInterval(updateSensorData, 3000); // 3초마다 업데이트
}

// 센서 데이터 업데이트
async function updateSensorData() {
    try {
        const response = await fetch('/api/sensors');
        if (!response.ok) throw new Error('센서 데이터 조회 실패');

        const data = await response.json();
        const tracker = data.system_status?.tracker || {};
        const environment = data.system_status?.environment || {};

        // 센서 값 업데이트
        document.getElementById('current-x-angle').textContent =
            tracker.motor_x_angle != null ? `${tracker.motor_x_angle}°` : '--°';
        document.getElementById('current-y-angle').textContent =
            tracker.motor_y_angle != null ? `${tracker.motor_y_angle}°` : '--°';
        document.getElementById('current-temp').textContent =
            environment.temperature != null ? `${environment.temperature}°C` : '--°C';
        document.getElementById('current-humidity').textContent =
            environment.humidity != null ? `${environment.humidity}%` : '--%';
        document.getElementById('current-mode').textContent = tracker.mode || '--';

    } catch (error) {
        console.error('센서 데이터 업데이트 오류:', error);
    }
}

// 슬라이더 값 업데이트
function updateSliderValue(axis) {
    const slider = document.getElementById(`${axis}-slider`);
    const valueDisplay = document.getElementById(`${axis}-value`);
    valueDisplay.textContent = slider.value;
}

// 모터 제어 적용
async function applyMotorControl() {
    const xAngle = parseInt(document.getElementById('x-slider').value);
    const yAngle = parseInt(document.getElementById('y-slider').value);

    try {
        const response = await fetch('/api/control/motor', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                x_angle: xAngle,
                y_angle: yAngle
            })
        });

        if (!response.ok) throw new Error('모터 제어 실패');

        const data = await response.json();
        addChatMessage(`모터 제어: X=${xAngle}°, Y=${yAngle}°`, 'bot');

        // 센서 데이터 즉시 업데이트
        setTimeout(updateSensorData, 500);

    } catch (error) {
        console.error('모터 제어 오류:', error);
        addChatMessage(`⚠️ 오류: ${error.message}`, 'bot');
    }
}

// 프리셋 설정
function setPreset(xAngle, yAngle) {
    document.getElementById('x-slider').value = xAngle;
    document.getElementById('y-slider').value = yAngle;
    updateSliderValue('x');
    updateSliderValue('y');
    applyMotorControl();
}

// AI 챗봇 메시지 전송
async function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();

    if (!message) return;

    // 사용자 메시지 추가
    addChatMessage(message, 'user');
    input.value = '';

    // 대화 이력에 추가
    conversationHistory.push({
        role: 'user',
        content: message
    });

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                conversation_history: conversationHistory
            })
        });

        if (!response.ok) throw new Error('AI 응답 실패');

        const data = await response.json();

        // AI 응답 추가
        addChatMessage(data.response, 'bot');

        // 대화 이력에 추가
        conversationHistory.push({
            role: 'assistant',
            content: data.response
        });

        // 액션이 있으면 슬라이더 업데이트
        if (data.action && data.action.type === 'motor_control') {
            document.getElementById('x-slider').value = data.action.x_angle;
            document.getElementById('y-slider').value = data.action.y_angle;
            updateSliderValue('x');
            updateSliderValue('y');

            // 센서 데이터 업데이트
            setTimeout(updateSensorData, 500);
        }

    } catch (error) {
        console.error('챗봇 오류:', error);
        addChatMessage(`⚠️ 오류: ${error.message}`, 'bot');
    }
}

// 채팅 메시지 추가
function addChatMessage(text, sender) {
    const chatContainer = document.getElementById('chat-container');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${sender}-message`;
    messageDiv.textContent = text;

    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Enter 키 이벤트 리스너 (이미 HTML에 있지만 백업용)
document.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && document.activeElement.id === 'chat-input') {
        sendMessage();
    }
});
