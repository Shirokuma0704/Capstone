"""Sensor aggregation for STGC without photodiodes.

This module attempts to read real sensors (GPS, INA219, DHT11/22) when
available and falls back to lightweight mock data if hardware or drivers are
missing. Photodiodes are intentionally excluded.
"""

import os
import random
import time
from typing import Any, Dict, Optional


class SensorReader:
    def __init__(self):
        self.mock_mode = os.getenv("USE_SENSOR_MOCK") == "1"
        self.gps_port = os.getenv("GPS_PORT", "/dev/ttyAMA0")
        self.gps_baud = int(os.getenv("GPS_BAUD", "9600"))
        self.dht_pin_name = os.getenv("DHT_PIN", "D17")  # board pin name
        self.i2c_bus_num = int(os.getenv("I2C_BUS", "3"))  # default to bus 3
        self._gps_serial = None
        self._ina = None
        self._dht = None

        if not self.mock_mode:
            self._setup_hardware()

    # --- Setup helpers ---
    def _setup_hardware(self):
        self._setup_gps()
        self._setup_ina219()
        self._setup_dht()

    def _setup_gps(self):
        try:
            import serial  # type: ignore

            self._gps_serial = serial.Serial(
                self.gps_port, self.gps_baud, timeout=1
            )
        except Exception as exc:  # pragma: no cover - hardware dependent
            print(f"GPS unavailable: {exc}")
            self._gps_serial = None

    def _setup_ina219(self):
        try:
            from adafruit_ina219 import INA219  # type: ignore

            i2c = None
            # Prefer explicitly configured bus (default 3). Requires adafruit_extended_bus.
            if self.i2c_bus_num:
                try:
                    import adafruit_extended_bus as exbus  # type: ignore

                    i2c = exbus.ExtendedI2C(self.i2c_bus_num)
                except Exception as exc:  # pragma: no cover - hardware dependent
                    print(f"INA219 unavailable on I2C bus {self.i2c_bus_num}: {exc}")
                    self._ina = None
                    return
            else:
                import board  # type: ignore
                import busio  # type: ignore

                i2c = busio.I2C(board.SCL, board.SDA)

            self._ina = INA219(i2c)
        except Exception as exc:  # pragma: no cover - hardware dependent
            print(f"INA219 unavailable: {exc}")
            self._ina = None

    def _setup_dht(self):
        try:
            import board  # type: ignore
            import adafruit_dht  # type: ignore

            pin = getattr(board, self.dht_pin_name)
            self._dht = adafruit_dht.DHT11(pin)
        except Exception as exc:  # pragma: no cover - hardware dependent
            print(f"DHT unavailable: {exc}")
            self._dht = None

    # --- Reading helpers ---
    def _read_gps(self) -> Dict[str, Optional[float]]:
        if self.mock_mode:
            return {
                "latitude": round(35.15 + random.uniform(-0.001, 0.001), 6),
                "longitude": round(129.05 + random.uniform(-0.001, 0.001), 6),
            }
        if not self._gps_serial:
            return {"latitude": None, "longitude": None}
        try:
            line = self._gps_serial.readline().decode(errors="ignore").strip()
            return self._parse_nmea(line)
        except Exception:
            return {"latitude": None, "longitude": None}

    @staticmethod
    def _parse_nmea(line: str) -> Dict[str, Optional[float]]:
        if not line.startswith("$GPGGA") and not line.startswith("$GPRMC"):
            return {"latitude": None, "longitude": None}

        parts = line.split(",")
        if line.startswith("$GPGGA") and len(parts) > 5:
            lat_raw, lat_dir, lon_raw, lon_dir = parts[2], parts[3], parts[4], parts[5]
        elif line.startswith("$GPRMC") and len(parts) > 6:
            lat_raw, lat_dir, lon_raw, lon_dir = parts[3], parts[4], parts[5], parts[6]
        else:
            return {"latitude": None, "longitude": None}

        def to_decimal(raw: str, direction: str) -> Optional[float]:
            if not raw or not direction:
                return None
            try:
                deg_len = 2 if direction in ("N", "S") else 3
                degrees = float(raw[:deg_len])
                minutes = float(raw[deg_len:])
                value = degrees + minutes / 60.0
                if direction in ("S", "W"):
                    value *= -1
                return value
            except Exception:
                return None

        return {
            "latitude": to_decimal(lat_raw, lat_dir),
            "longitude": to_decimal(lon_raw, lon_dir),
        }

    def _read_ina219(self) -> Dict[str, Optional[float]]:
        if self.mock_mode:
            voltage = round(12.0 + random.uniform(-0.5, 0.5), 2)
            current = round(0.25 + random.uniform(-0.1, 0.1), 3)
            power = round(voltage * current, 2)
            return {"voltage": voltage, "current": current, "power": power}

        if not self._ina:
            return {"voltage": None, "current": None, "power": None}
        try:
            voltage = float(self._ina.bus_voltage)
            current = float(self._ina.current) / 1000.0  # mA -> A
            power = voltage * current
            return {"voltage": voltage, "current": current, "power": power}
        except Exception:
            return {"voltage": None, "current": None, "power": None}

    def _read_dht(self) -> Dict[str, Optional[float]]:
        if self.mock_mode:
            return {
                "temperature": round(25.0 + random.uniform(-2, 2), 1),
                "humidity": round(50.0 + random.uniform(-5, 5), 1),
            }
        if not self._dht:
            return {"temperature": None, "humidity": None}
        try:
            return {
                "temperature": float(self._dht.temperature),
                "humidity": float(self._dht.humidity),
            }
        except Exception:
            return {"temperature": None, "humidity": None}

    # --- Public API ---
    def read_all(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "timestamp": time.time(),
        }
        data.update(self._read_ina219())
        data.update(self._read_dht())
        data.update(self._read_gps())
        return data


if __name__ == "__main__":
    reader = SensorReader()
    print(reader.read_all())
