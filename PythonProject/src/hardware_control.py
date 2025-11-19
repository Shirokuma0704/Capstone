import random
import time

class HardwareControl:
    """
    A mock hardware control class to simulate interactions with the STGC hardware.
    In a real-world scenario, this class would interface with RPi.GPIO,
    sensor libraries, etc.
    """
    def __init__(self):
        self.x_angle = 90
        self.y_angle = 90
        print("Initialized Mock Hardware Control")

    def set_panel_angle(self, axis, angle):
        """
        Simulates setting the solar panel angle.
        :param axis: "x" or "y"
        :param angle: The angle to set (0-180)
        :return: A status message.
        """
        try:
            angle = int(angle)
            if not (0 <= angle <= 180):
                raise ValueError("Angle must be between 0 and 180.")

            if axis.lower() == 'x':
                self.x_angle = angle
                message = f"X-axis (horizontal) motor moved to {angle} degrees."
            elif axis.lower() == 'y':
                self.y_angle = angle
                message = f"Y-axis (vertical) motor moved to {angle} degrees."
            else:
                raise ValueError("Axis must be 'x' or 'y'.")
            
            print(f"SIMULATING: {message}")
            return {"status": "success", "message": message}
        except ValueError as e:
            return {"status": "error", "message": str(e)}

    def get_current_status(self):
        """
        Simulates getting the current status from all sensors.
        :return: A dictionary with the current (randomized) sensor data.
        """
        status = {
            "timestamp": time.time(),
            "panel_angle_x": self.x_angle,
            "panel_angle_y": self.y_angle,
            "voltage": round(12.0 + random.uniform(-0.5, 0.5), 2),
            "current": round(0.25 + random.uniform(-0.1, 0.1), 3),
            "power": round(3.0 + random.uniform(-0.5, 0.5), 2),
            "temperature": round(25.0 + random.uniform(-2.0, 2.0), 1),
            "humidity": round(50.0 + random.uniform(-5.0, 5.0), 1),
            "gps_fix": True,
            "latitude": 35.15,
            "longitude": 129.05,
        }
        print(f"SIMULATING: get_current_status -> {status}")
        return status

if __name__ == '__main__':
    # Example usage:
    hw = HardwareControl()
    print(hw.get_current_status())
    print(hw.set_panel_angle("x", 120))
    print(hw.get_current_status())
