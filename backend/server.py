from flask import Flask, jsonify, request
from flask_cors import CORS
import datetime

app = Flask(__name__)
CORS(app)

# === CONFIG ROUTE ===


# === In-memory state (replace with DB or file persistence later) ===
relay_states = {"relay1": 0, "relay2": 1, "relay3": 1, 'timestamp': 0, "mode": "auto"}
measurements = {"temp_dht22": 0, "temp_ds18b20": 0, "humidity": 0}
control_mode = {"mode": "auto"}
control_config = {"temp_start_compressor": 4.5, "temp_stop_compressor": 3.5}

# === Root ===
@app.route("/")
def home():
    return jsonify({"status": "ok"}), 200

@app.route("/api/message")
def get_message():
    return jsonify({"message": "Hello from Flask!"})

# === RELAY ROUTES ===
@app.route("/api/relay", methods=["POST"])
def set_relay_state():
    global relay_states
    data = request.get_json()
    relay_states.update(data)

    for relay, state in relay_states.items():
        relay_states[relay] = 0 if state == 1 else 1
    print("Updated relay states:", relay_states)
    return jsonify({"status": "ok", "received": relay_states})

@app.route("/api/relay-state", methods=["GET", "POST"])
def relay_state():
    global relay_states
    if request.method == "POST":
        data = request.get_json()
        if relay_states['timestamp'] < data['timestamp'] and control_mode['mode'] == data['mode']:
            relay_states = data

        print("Updated relay states via POST:", relay_states)
        return jsonify({"status": "ok"})
    
    print("Forwarding relay states: ", relay_states)
    return jsonify(relay_states)

# === SENSOR ROUTES ===
@app.route("/api/sensors", methods=["POST", "GET"])
def sensors():
    if request.method == "POST":
        data = request.get_json()
        print("Received sensor data:", data)
        measurements["temp_dht22"] = data.get("temp_dht22")
        measurements["humidity"] = data.get("humidity")
        measurements["temp_ds18b20"] = data.get("temp_ds18b20")
        measurements["timestamp"] = datetime.datetime.now().isoformat()
        return jsonify({"status": "ok"})
    return jsonify(measurements)

# === MODE ROUTES ===
@app.route("/api/mode", methods=["GET", "POST"])
def mode():
    global control_mode
    if request.method == "POST":
        data = request.get_json()
        mode_value = data.get("mode")
        if mode_value in ["auto", "manual"]:
            control_mode["mode"] = mode_value
            print(f"Control mode set to: {mode_value}")
            return jsonify({"status": "ok", "mode": mode_value})
        else:
            return jsonify({"status": "error", "message": "Invalid mode"}), 400
    return jsonify(control_mode)

# === CONFIG ROUTES (setpoints) ===
@app.route("/api/config", methods=["GET", "POST"])
def config():
    global control_config
    if request.method == "POST":
        data = request.get_json()
        start_temp = data.get("temp_start_compressor")
        stop_temp = data.get("temp_stop_compressor")

        # Validate range
        if (
            isinstance(start_temp, (int, float))
            and isinstance(stop_temp, (int, float))
            and 0 <= stop_temp < start_temp <= 50
        ):
            control_config["temp_start_compressor"] = float(start_temp)
            control_config["temp_stop_compressor"] = float(stop_temp)
            print("Updated control config:", control_config)
            return jsonify({"status": "ok", "config": control_config})
        else:
            return jsonify({"status": "error", "message": "Invalid config values"}), 400
    return jsonify(control_config)

# === STATUS ROUTE (optional combined data) ===
@app.route("/api/status")
def status():
    """Return combined status info: mode, relays, sensors, config."""
    status_info = {
        "mode": control_mode["mode"],
        "relays": relay_states,
        "measurements": measurements,
        "config": control_config,
    }
    return jsonify(status_info)

# === MAIN ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)
