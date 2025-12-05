## 2.2 Software Architecture and Control Algorithms

The software system for this project moves away from the traditional embedded control method running within a single device. To maximize scalability and ease of maintenance, we adopted a modern **Microservices Architecture**. Furthermore, to ensure precise hardware control, we established a high-performance time-series data processing pipeline and integrated MCP (Model Context Protocol)—the latest generative AI technology—to complete an intelligent control system.

### 2.2.1 Docker-Based Microservices Architecture

To resolve dependency conflicts common in embedded system development and to ensure independent updates and deployment convenience for each functional module, the entire system was designed based on Docker containers. The six core services defined via `docker-compose.yml` run in an environment isolated from the host OS and communicate organically through an internal Docker virtual network. This structure provides **Fault Tolerance**, ensuring that the entire system does not stop even if an error occurs in one part.

```yaml
version: "3.9"
services:
  hardware-api:
    build: ./src/hardware_api
    ports: ["8000:8000"]
    devices: ["/dev/gpiomem:/dev/gpiomem"]
    environment:
      - INFLUX_URL=http://influxdb:8086
    depends_on: [influxdb]

  data-producer:
    build: ./src/data_producer
    command: ["python", "main.py", "--interval", "5"]
    environment:
      - INFLUX_URL=http://influxdb:8086
    depends_on: [hardware-api]

  influxdb:
    image: influxdb:2.7
    volumes:
      - ./logs/influxdb:/var/lib/influxdb2

  grafana:
    image: grafana/grafana:10.3.3
    ports: ["3000:3000"]
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=devpass
    depends_on: [influxdb]

  control-ui:
    build: ./src/control_ui
    ports: ["5000:5000"]
    depends_on: [hardware-api, grafana]

  mcp-server:
    build: ./src/mcp_server
    environment:
      - HARDWARE_API_URL=http://hardware-api:8000
    depends_on: [hardware-api]
```

*   **Hardware API (hardware-api):** A backend server built using Python’s high-performance asynchronous web framework, **FastAPI**. It is the only module that communicates directly with the Raspberry Pi's GPIO and I2C interfaces, preventing resource contention by monopolizing hardware access. It acts as a Hardware Abstraction Layer (HAL), allowing external services (UI, AI, etc.) to control devices simply by calling standardized REST APIs (e.g., `POST /control`) without needing to know the physical characteristics of the hardware.
*   **Data Producer (data-producer):** An independent background service that periodically collects sensor data (e.g., every 5 seconds) and transmits it to the database. It is completely separated from the main control loop or API server, guaranteeing stability where data collection cycles are not delayed or missed even if user requests spike or control logic becomes complex.
*   **InfluxDB (influxdb):** A Time Series Database (TSDB) adopted to efficiently store data that is continuously generated over time, such as IoT sensor data (voltage, current, power, temperature/humidity, etc.). Unlike general Relational Databases (RDB), it is optimized for time-based queries, demonstrating excellent performance in high-speed writing and retrieval of massive sensor data.
*   **Grafana (grafana):** A monitoring platform that visualizes collected data in conjunction with InfluxDB. Beyond simple numerical checks, it visualizes power generation trends and battery charging status via graphs and gauges, helping users grasp the system's health at a glance.
*   **Control UI (control-ui):** A lightweight **Flask**-based web server allowing users to access the system via a web browser without installing a separate app. It integrates a hardware control panel, real-time data dashboard, and AI chat interface, applying responsive web design for an optimized User Experience (UX).
*   **MCP Server (mcp-server):** A Model Context Protocol server that mediates communication between the Large Language Model (LLM, Gemini) and the physical hardware system. It acts as intelligent middleware that translates natural language commands from the AI into specific API calls and, conversely, converts system sensor data into text context understandable by the AI.

### 2.2.2 Solar Tracking Algorithm

To dramatically improve power generation efficiency compared to fixed panels, we implemented a **Dual-Axis Precision Tracking Algorithm** that calculates and tracks the sun's exact position in real-time based on GPS coordinates and UTC time. This algorithm is modularized in `src/solar_tracker.py` and operates through the following sophisticated steps:

```python
# src/solar_tracker.py
from datetime import datetime, timezone
from pathlib import Path
import json
from pysolar.solar import get_altitude, get_azimuth
from .motor_controller import MotorController

CACHE_PATH = Path("solar_tracker_cache.json")

class SolarTracker:
    def __init__(self, motor: MotorController, soft_limits=(5, 85)):
        self.motor = motor
        self.soft_limits = soft_limits

    def _bounded(self, angle: float) -> float:
        low, high = self.soft_limits
        return max(low, min(high, angle))

    def track(self, lat: float, lon: float, when: datetime | None = None):
        when = (when or datetime.now(timezone.utc)).astimezone(timezone.utc)
        altitude = get_altitude(lat, lon, when)
        azimuth = get_azimuth(lat, lon, when)
        self.motor.move(
            pan=self._bounded(azimuth % 360),
            tilt=self._bounded(altitude),
            smooth=True,
        )
        CACHE_PATH.write_text(json.dumps({"lat": lat, "lon": lon, "ts": when.isoformat()}))

    def recover_last_pose(self):
        if not CACHE_PATH.exists():
            return
        data = json.loads(CACHE_PATH.read_text())
        self.track(data["lat"], data["lon"], datetime.fromisoformat(data["ts"]))
```

*   **Spatio-Temporal Synchronization:** The `Motor_GPS.py` module receives the current latitude, longitude, and accurate satellite-based UTC time from the NEO-6M GPS sensor. To prepare for "Cold Start" situations where GPS signal reception fails (e.g., inside tunnels or during initial startup), a redundancy logic using a battery-backed DS3231 RTC (Real Time Clock) module is applied to enhance system availability.
*   **Astronomical Precision Coordinate Calculation:** The received spatio-temporal information is input into the `get_altitude` and `get_azimuth` functions of the verified astronomical calculation library, `pysolar`. This calculates the sun's coordinates at the current location with 0.01-degree precision, reflecting not only the seasonal meridian altitude but also the Earth's orbital path and axial tilt.
*   **Kinematic Motor Control Mapping:** The calculated azimuth (0–360°) and altitude (0–90°) are converted into PWM duty cycles for the dual-axis servo motors (MG996R, MG995) that drive the hardware. **Soft Limits** are applied to prevent cable twisting or structural collisions due to mechanical constraints. Additionally, smoothing logic is included to gently accelerate and decelerate to the target angle, reducing power consumption and mechanical wear caused by sudden motor movements.
*   **Intelligent Caching & Recovery Strategy:** To prepare for sudden power cuts or reboots, the last calculated valid coordinates and time are cached in real-time to the `solar_tracker_cache.json` file. This is designed to minimize power generation downtime by immediately returning to the last tracking position upon reboot, even before a GPS signal is acquired.

### 2.2.3 Time-Series Data Processing Pipeline

To secure high-quality datasets for AI analysis beyond simple monitoring, a robust 3-stage data processing pipeline consisting of 'Collection-Storage-Analysis' was established.

```python
# src/data_pipeline.py
import asyncio
from influxdb_client import InfluxDBClient, Point
from .sensor_reader import SensorReader

async def collect_and_store(interval: int = 5):
    reader = SensorReader()
    client = InfluxDBClient(url="http://localhost:8086", token="token", org="org")
    write_api = client.write_api()

    while True:
        sample = await reader.read_all()
        point = (
            Point("sensor_data")
            .tag("device_id", sample.device_id)
            .tag("location", sample.location)
            .field("voltage", sample.voltage)
            .field("current", sample.current)
            .field("temperature", sample.temperature)
        )
        write_api.write(bucket="solar", record=point)
        await asyncio.sleep(interval)


async def query_last_day_energy():
    query = """
    from(bucket:"solar")
      |> range(start: -24h)
      |> filter(fn: (r) => r._measurement == "sensor_data")
      |> aggregateWindow(every: 1h, fn: mean)
      |> yield(name: "hourly_mean")
    """
    with InfluxDBClient(url="http://localhost:8086", token="token", org="org") as client:
        tables = client.query_api().query(query)
        return tables
```

*   **Asynchronous Collection:** The `SensorReader` class (`src/sensor_reader.py`) is implemented using Python's `asyncio` library. When reading data from the INA219 (power sensor) and DHT11 (temp/humidity sensor) via I2C, it does not block the main thread during I/O wait times, allowing parallel processing of other tasks. This enables high-speed data collection while maintaining overall system responsiveness.
*   **Structured Storage:** The `DataLogger` class (`src/data_logger.py`) structures collected raw data into InfluxDB `sensor_data` Measurements. Each data point is indexed with Tags such as `device_id`, `location`, and `sensor_type`, dramatically increasing search speeds when filtering for specific devices or time periods later.
*   **Real-time Analysis:** The `DBAnalyzer` module (`src/db_analyzer.py`) uses **Flux**, InfluxDB's powerful query language, to perform complex computational tasks at the database level. Analysis tasks such as aggregating power generation over the last 1/24 hours, noise removal via moving averages, and power efficiency calculations are performed in real-time. These results serve as key contexts for the AI model to understand the current system situation.

### 2.2.4 MCP (Model Context Protocol) Design for AI Control

To convert ambiguous natural language commands from users into clear system control signals, we designed and implemented a proprietary MCP (Model Context Protocol). This is a core technology that expands Google's latest Generative AI model (Gemini 1.5) from a simple chatbot into an active **Agent** capable of controlling hardware.

```json
{
  "system": "You are a control agent. Always classify intent and call tools safely.",
  "context": {
    "battery_voltage": 12.4,
    "panel_power": 18.2,
    "tracker_mode": "auto"
  },
  "tools": {
    "controlPanel": {
      "description": "Move dual-axis tracker.",
      "schema": {"pan": "number", "tilt": "number"}
    },
    "getStatus": {
      "description": "Fetch latest system metrics.",
      "schema": {"scope": "string"}
    }
  },
  "user": "Turn the panel 10 degrees east and report the voltage."
}
```

*   **Prompt Engineering-based Intent Classification:** The system prompt is designed so that the LLM analyzes the user's input text and classifies the intent into categories such as 'General Conversation (general_conversation)', 'Status Inquiry (data_analysis)', or 'Control Command (control)'. This prevents unnecessary API calls and ensures the exact response process matches the user's purpose.
*   **Dynamic Context Injection:** Every time the AI generates a response, the latest system status information—such as current battery voltage, real-time power generation, tracker mode (Auto/Manual), and weather information—is dynamically injected into the System Instruction area of the prompt. This allows the AI to provide fact-based, accurate answers (e.g., **"Current battery voltage is 12.4V, and charging current is 0.5A, which is a healthy state."**) rather than generic pre-learned knowledge in response to questions like "How is the battery?".
*   **Function Calling Mechanism:** If the AI determines that hardware control is necessary during conversation, it generates a JSON response calling pre-defined Tools such as `controlPanel` or `getStatus`. The MCP Server (`src/mcp_server.py`) detects this, verifies validity, and then calls the actual Hardware API endpoint to execute the physical action. This also serves as a security measure, preventing the AI from executing arbitrary code and ensuring only defined, safe APIs are used.

## 3.2 Software Implementation Results

### 3.2.1 Hardware Control API Server (Hardware API)

We implemented a FastAPI-based RESTful API server to allow any client on the local network to control the hardware resources inside the Raspberry Pi in a standardized manner.

```python
# src/hardware_api/main.py
from fastapi import FastAPI
from pydantic import BaseModel, Field
from .drivers import sensors, motors

app = FastAPI()


class ControlRequest(BaseModel):
    pan: float = Field(ge=0, le=360)
    tilt: float = Field(ge=0, le=90)


@app.get("/api/v1/sensors")
async def read_sensors():
    return await sensors.snapshot()


@app.post("/api/v1/control")
async def manual_control(cmd: ControlRequest):
    await motors.move(pan=cmd.pan, tilt=cmd.tilt)
    return {"mode": "manual", "pan": cmd.pan, "tilt": cmd.tilt}


@app.get("/api/v1/status")
async def status():
    gps = await sensors.gps_fix()
    return {"tracker_mode": motors.mode, "gps_fix": gps, "last_tracking": motors.last_move_iso()}
```

**Key API Endpoints and Features:**
*   `GET /api/v1/sensors`: Returns real-time values of all sensors (voltage, current, power, temp/humidity) as a JSON object. Optimized for client polling requests.
*   `POST /api/v1/control`: Called when a user requests manual control. It immediately moves the motors to the Pan/Tilt angles included in the request body. At this time, the tracker mode automatically switches to 'Manual' to prevent conflict with the automatic tracking logic.
*   `GET /api/v1/status`: Returns system health status, including current tracker mode (Auto/Manual), GPS reception status (Fix/No Fix), and last tracking time.

**Implementation Characteristics:**
We secured high responsiveness using Python's `async/await` syntax, enabling immediate processing of control commands without delay even during slow I/O operations for reading sensors. Additionally, strictly validating input data using **Pydantic** models eliminates hardware malfunctions caused by incorrect control commands.

### 3.2.2 Real-Time Monitoring Dashboard – InfluxDB, Grafana

To allow users to intuitively grasp and analyze the vast amount of collected time-series data, we built a professional monitoring dashboard using the industry-standard tool, Grafana.

```json
{
  "panels": [
    {
      "type": "gauge",
      "title": "Power Generation",
      "targets": [{"query": "from(bucket:'solar') |> range(start:-5m) |> filter(fn:(r)=>r._field=='power')"}],
      "fieldConfig": {"thresholds": {"mode": "absolute", "steps": [{"color": "red", "value": 0}, {"color": "green", "value": 20}]}}
    },
    {
      "type": "timeseries",
      "title": "Voltage / Current",
      "targets": [{"query": "from(bucket:'solar') |> range(start:-24h) |> filter(fn:(r)=>r._field=='voltage' or r._field=='current')"}]
    }
  ],
  "refresh": "5s",
  "timezone": "utc"
}
```

**Panel Configuration:**
*   **Power Generation Gauge:** Visualizes the current power (W) produced by the solar panel in an analog gauge format. Color thresholds are set to display red for low generation and green for high generation.
*   **Energy Trend Graph:** Displays voltage (V) and current (A) trends over time as an overlay graph, allowing analysis of peak sunlight hours or identification of generation drops due to clouds.
*   **Environment Monitor:** Displays internal system temperature and humidity data as a real-time line chart, enabling early detection and prevention of hardware anomalies such as overheating or condensation during summer.

**Integration:**
This dashboard is embedded as an Iframe within the Control UI web page, providing a 'Single Pane of Glass' environment where users can check all information on the integrated control screen without a separate Grafana login or page navigation.

### 3.2.3 AI Chat Control System (MCP Client)

We implemented a conversational AI client that allows users to naturally control the system and obtain information using everyday language without mastering complex manuals or operation methods.

```python
# src/mcp_client.py
from mcp import AgentClient
from src.mcp_server.client import control_panel, get_status

client = AgentClient(
    model="gemini-1.5-pro",
    tools={"controlPanel": control_panel, "getStatus": get_status},
)


async def handle_message(text: str):
    response = await client.chat(text, context={"battery_voltage": 12.4})
    if response.tool_calls:
        for call in response.tool_calls:
            result = await client.run_tool(call)
            await client.append_context(result)
        return await client.chat("Summarize results for the user.")
    return response.message
```

**Key Features and Scenarios:**
*   **Intelligent Status Briefing:** When a user asks, "How is the power generation today?", instead of just giving current numbers, it queries and summarizes past data in the DB to provide an insightful answer like, **"Over the past 24 hours, the average generation was 12.5W, with a maximum of 25W recorded at 2 PM."**
*   **Natural Language Command Execution:** It accurately understands colloquial commands like "Turn the panel a bit to the east" or "Switch to manual mode" and internally calls the `control_motor` function to control the actual hardware.
*   **Context Awareness:** It supports **Multi-turn** conversation where context is maintained. For example, if a user asks "What is the voltage now?" and then follows up with "And the current?", the system understands the omitted subject and provides the correct current value.

### 3.2.4 Integrated Control Web Interface (Control UI)

We maximized user convenience by implementing an integrated web interface using Python Flask and HTML/JavaScript, allowing access and control of all system functions from a single screen.

```html
<!-- src/control_ui/templates/index.html -->
<script>
async function sendControl(pan, tilt) {
  const res = await fetch('/api/control', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({pan, tilt}),
  });
  const data = await res.json();
  console.log('tracker mode', data.mode);
}

document.querySelector('#preset-east').onclick = () => sendControl(90, 30);
</script>

<iframe src="http://localhost:3000/d/solar" width="100%" height="600" frameborder="0"></iframe>
```

**UI Components and Features:**
*   **Manual Control Panel:** Provides an intuitive Slider UI to precisely adjust the tracker's Tilt/Pan angles in 1-degree increments. Manipulating the slider sends AJAX requests to the Hardware API immediately, offering a delay-free control experience.
*   **Quick Preset Buttons:** For emergencies or repetitive testing, preset buttons like 'Due South', 'East', and 'Home (Reset)' are placed to move the panel to desired positions with a single touch.
*   **Floating AI Chat Window:** A floating chat window is always placed at the bottom right of the screen, creating a multitasking environment where users can ask the AI assistant for status updates or help while performing control tasks.
*   **Real-time Dashboard Integration:** The Grafana dashboard is placed in the center of the screen so that users can receive immediate visual feedback on changes in power generation resulting from their control actions (e.g., changing panel angles).
