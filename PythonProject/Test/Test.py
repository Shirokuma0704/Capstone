#!/usr/bin/env python3
"""
서보모터 핀 연결 확인 테스트 코드
GPIO 핀 12번, 33번에 연결된 서보모터를 테스트합니다.
"""

import RPi.GPIO as GPIO
import time
import sys

# 핀 번호 설정 (BOARD 모드 사용)
SERVO_PIN_1 = 12  # 물리적 핀 12번 (GPIO18)
SERVO_PIN_2 = 33  # 물리적 핀 33번 (GPIO13)


def setup_gpio():
    """GPIO 초기 설정"""
    try:
        GPIO.setmode(GPIO.BOARD)  # 물리적 핀 번호 사용
        GPIO.setwarnings(False)
        print("✓ GPIO 모드 설정 완료 (BOARD 모드)")
        return True
    except Exception as e:
        print(f"✗ GPIO 설정 실패: {e}")
        return False


def test_pin_setup(pin_number):
    """특정 핀의 설정 테스트"""
    try:
        GPIO.setup(pin_number, GPIO.OUT)
        print(f"✓ 핀 {pin_number}번 출력 모드 설정 완료")
        return True
    except Exception as e:
        print(f"✗ 핀 {pin_number}번 설정 실패: {e}")
        return False


def test_pwm_setup(pin_number, frequency=50):
    """PWM 신호 생성 테스트"""
    try:
        pwm = GPIO.PWM(pin_number, frequency)
        print(f"✓ 핀 {pin_number}번 PWM 생성 완료 (주파수: {frequency}Hz)")
        return pwm
    except Exception as e:
        print(f"✗ 핀 {pin_number}번 PWM 생성 실패: {e}")
        return None


def test_servo_movement(pwm, pin_number):
    """서보모터 동작 테스트"""
    print(f"\n핀 {pin_number}번 서보모터 동작 테스트 중...")

    try:
        # 서보모터 시작
        pwm.start(0)
        time.sleep(0.5)

        # 0도 위치 (duty cycle 2.5%)
        print(f"  → 0도 위치로 이동...")
        pwm.ChangeDutyCycle(2.5)
        time.sleep(1)

        # 90도 위치 (duty cycle 7.5%)
        print(f"  → 90도 위치로 이동...")
        pwm.ChangeDutyCycle(7.5)
        time.sleep(1)

        # 180도 위치 (duty cycle 12.5%)
        print(f"  → 180도 위치로 이동...")
        pwm.ChangeDutyCycle(12.5)
        time.sleep(1)

        # 90도로 복귀
        print(f"  → 90도 위치로 복귀...")
        pwm.ChangeDutyCycle(7.5)
        time.sleep(1)

        # PWM 신호 정지
        pwm.ChangeDutyCycle(0)

        print(f"✓ 핀 {pin_number}번 서보모터 동작 테스트 완료")
        return True

    except Exception as e:
        print(f"✗ 핀 {pin_number}번 서보모터 동작 실패: {e}")
        return False


def main():
    """메인 테스트 함수"""
    print("=" * 50)
    print("서보모터 핀 연결 테스트 시작")
    print("=" * 50)
    print(f"테스트 핀: {SERVO_PIN_1}번, {SERVO_PIN_2}번\n")

    # GPIO 초기화
    if not setup_gpio():
        print("\nGPIO 설정 실패로 테스트를 중단합니다.")
        return

    print("\n" + "-" * 50)
    print(f"1. 핀 {SERVO_PIN_1}번 테스트")
    print("-" * 50)

    # 첫 번째 서보모터 (핀 12) 테스트
    if test_pin_setup(SERVO_PIN_1):
        pwm1 = test_pwm_setup(SERVO_PIN_1)
        if pwm1:
            test_servo_movement(pwm1, SERVO_PIN_1)
            pwm1.stop()

    print("\n" + "-" * 50)
    print(f"2. 핀 {SERVO_PIN_2}번 테스트")
    print("-" * 50)

    # 두 번째 서보모터 (핀 33) 테스트
    if test_pin_setup(SERVO_PIN_2):
        pwm2 = test_pwm_setup(SERVO_PIN_2)
        if pwm2:
            test_servo_movement(pwm2, SERVO_PIN_2)
            pwm2.stop()

    # 동시 동작 테스트
    print("\n" + "-" * 50)
    print("3. 두 서보모터 동시 동작 테스트")
    print("-" * 50)

    try:
        GPIO.setup(SERVO_PIN_1, GPIO.OUT)
        GPIO.setup(SERVO_PIN_2, GPIO.OUT)

        pwm1 = GPIO.PWM(SERVO_PIN_1, 50)
        pwm2 = GPIO.PWM(SERVO_PIN_2, 50)

        pwm1.start(0)
        pwm2.start(0)
        time.sleep(0.5)

        print("  → 두 서보모터 동시 0도")
        pwm1.ChangeDutyCycle(2.5)
        pwm2.ChangeDutyCycle(2.5)
        time.sleep(1)

        print("  → 두 서보모터 동시 90도")
        pwm1.ChangeDutyCycle(7.5)
        pwm2.ChangeDutyCycle(7.5)
        time.sleep(1)

        print("  → 두 서보모터 동시 180도")
        pwm1.ChangeDutyCycle(12.5)
        pwm2.ChangeDutyCycle(12.5)
        time.sleep(1)

        print("  → 중앙 위치로 복귀")
        pwm1.ChangeDutyCycle(7.5)
        pwm2.ChangeDutyCycle(7.5)
        time.sleep(1)

        pwm1.ChangeDutyCycle(0)
        pwm2.ChangeDutyCycle(0)
        pwm1.stop()
        pwm2.stop()

        print("✓ 동시 동작 테스트 완료")

    except Exception as e:
        print(f"✗ 동시 동작 테스트 실패: {e}")

    # GPIO 정리
    GPIO.cleanup()

    print("\n" + "=" * 50)
    print("테스트 완료 및 GPIO 정리 완료")
    print("=" * 50)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n사용자에 의해 테스트가 중단되었습니다.")
        GPIO.cleanup()
        sys.exit(0)
    except Exception as e:
        print(f"\n오류 발생: {e}")
        GPIO.cleanup()
        sys.exit(1)