import smbus2
import time

# ==========================================
# 설정: 3번 버스 (Software I2C)
# ==========================================
I2C_BUS = 3
ADDR = 0x40

try:
    bus = smbus2.SMBus(I2C_BUS)
except Exception as e:
    print(f"❌ I2C 버스 {I2C_BUS}번을 열 수 없습니다. 설정을 확인하세요.")
    exit()


def write_register(reg, value):
    """16비트 데이터를 Big-endian으로 기록"""
    # INA219는 Big-endian을 받으므로 바이트 순서를 뒤집어서 보냄
    val_swapped = ((value & 0xFF) << 8) | (value >> 8)
    try:
        bus.write_word_data(ADDR, reg, val_swapped)
    except OSError:
        print(f"❌ 레지스터 0x{reg:02X} 쓰기 실패")


def read_register(reg):
    """16비트 레지스터 읽기 (Big-endian 처리)"""
    try:
        val = bus.read_word_data(ADDR, reg)
        # 리틀 엔디안(Pi) -> 빅 엔디안(INA219) 변환
        val_swapped = ((val & 0xFF) << 8) | (val >> 8)
        return val_swapped
    except OSError:
        return None


def get_signed_value(val):
    """16비트 부호 있는 정수 처리 (2의 보수)"""
    if val > 32767:
        val -= 65536
    return val


print(f"🔍 INA219 (0x{ADDR:X}) 모든 레지스터 모니터링 시작...")
print("=" * 60)

# 1. [중요] 캘리브레이션 레지스터(0x05) 설정
# 캘리브레이션 값이 0이면 Current(0x04)와 Power(0x03) 레지스터는 작동하지 않습니다.
# 테스트를 위해 일반적인 값(4096)을 강제로 입력합니다.
write_register(0x05, 4096)
time.sleep(0.1)  # 적용 대기

# 2. 모든 레지스터 읽기 및 해석
registers = {
    0x00: "Configuration",
    0x01: "Shunt Voltage",
    0x02: "Bus Voltage  ",
    0x03: "Power        ",
    0x04: "Current      ",
    0x05: "Calibration  "
}

for reg_addr, reg_name in registers.items():
    raw_val = read_register(reg_addr)

    if raw_val is None:
        print(f"ADDR 0x{reg_addr:02X} | {reg_name} | ❌ 읽기 실패 (I/O Error)")
        continue

    # 데이터 해석 (DataSheet 기준)
    explanation = ""

    if reg_addr == 0x00:  # Config
        explanation = f"기본값: 0x399F ({'✅ 정상' if raw_val == 0x399F else '⚠️ 변경됨'})"

    elif reg_addr == 0x01:  # Shunt Voltage (저항 양단 전압)
        # 1 LSB = 10 uV
        signed_val = get_signed_value(raw_val)
        val_mv = signed_val * 0.01
        explanation = f"{val_mv:.3f} mV (부하 전류 흐를 때 증가)"

    elif reg_addr == 0x02:  # Bus Voltage (측정 전압)
        # 3~15비트 사용, 1 LSB = 4 mV
        val_v = (raw_val >> 3) * 0.004
        explanation = f"{val_v:.3f} V (배터리 전압)"

    elif reg_addr == 0x03:  # Power (전력)
        explanation = f"Raw: {raw_val} (계산 필요)"

    elif reg_addr == 0x04:  # Current (전류)
        # Calibration 값에 따라 달라짐
        signed_current = get_signed_value(raw_val)
        explanation = f"Raw: {signed_current} (계산 필요)"

    elif reg_addr == 0x05:  # Calibration
        explanation = f"설정값 (0이면 전류 측정 불가)"

    # 출력 포맷팅
    print(f"0x{reg_addr:02X} | {reg_name} | Hex: 0x{raw_val:04X} | {explanation}")

print("=" * 60)
print("📌 참고: 배터리 미연결 시 Voltage는 0V 근처, Current는 0이 정상입니다.")