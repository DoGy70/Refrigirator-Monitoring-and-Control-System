import os
import glob
import time
import requests
import RPi.GPIO as GPIO
import adafruit_dht
import board
import json

# === Configuration ===
API_SENSOR_URL = "http://192.168.100.171:5050/api/sensors"
API_RELAY_URL  = "http://192.168.100.171:5050/api/relay-state"
API_MODE_URL   = "http://192.168.100.171:5050/api/mode"
API_CONFIG_URL = "http://192.168.100.171:5050/api/config"
STATE_FILE = "system_state.json"

RELAY_PINS = {"relay1": 26, "relay2": 20, "relay3": 21}
current_state = {
    "config": {"temp_start_compressor": 4.5, "temp_stop_compressor": 3.5}
}

# Intervals
SENSOR_READ_INTERVAL = 2        # seconds
UPLOAD_INTERVAL = 60            # seconds
CHECK_POLL_INTERVAL = 4         # seconds
SAVE_STATE_INTERVAL = 120       # seconds

# === Sensor setup ===
os.system("modprobe w1-gpio")
os.system("modprobe w1-therm")
base_dir = "../../../sys/bus/w1/devices/"

device_folder = glob.glob(base_dir + "28*")[0]
device_file = device_folder + "/w1_slave"

dht22 = adafruit_dht.DHT22(board.D4, use_pulseio=False)

# === Functions ===

def save_state(data):
    """Save current system state to file"""
    data["timestamp"] = int(time.time())
    with open(STATE_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print(f"State saved at {time.ctime(data['timestamp'])}")

def load_state():
    """Load previous system state from file if available"""
    if not os.path.exists(STATE_FILE):
        print("No saved state found, starting fresh.")
        return None
    
    with open(STATE_FILE, "r") as f:
        state = json.load(f)
    print(f"Restored state from {time.ctime(state['timestamp'])}")
    return state

def read_temp_raw():
    with open(device_file, "r") as f:
        return f.readlines()

def read_temp_ds18b20():
    lines = read_temp_raw()
    while lines[0].strip()[-3:] != "YES":
        time.sleep(0.2)
        lines = read_temp_raw()
    equals_pos = lines[1].find("t=")
    if equals_pos != -1:
        temp_string = lines[1][equals_pos + 2:]
        temp_c = float(temp_string) / 1000.0
        return temp_c

def read_temp():
    """Read measurements"""
    try:
        temperature = dht22.temperature
        humidity = dht22.humidity
        temp_ds18b20 = read_temp_ds18b20()
        return temperature, humidity, temp_ds18b20
    except RuntimeError as err:
        print(err.args[0])
        return None, None, None

def send_temp(temp_dht22, humidity, temp_ds18b20):
    """Send measurements to the server"""
    try:
        if temp_dht22 and humidity and temp_ds18b20:
            data = {
                "temp_dht22": temp_dht22,
                "humidity": humidity,
                "temp_ds18b20": temp_ds18b20
            }
            response = requests.post(API_SENSOR_URL, json=data, timeout=5)
            print("Sensor data sent:", response.status_code)
    except requests.RequestException as e:
        print("Error contacting server:", e)

def setup_gpio():
    """Setup GPIO for use"""
    GPIO.setmode(GPIO.BCM)
    for pin in RELAY_PINS.values():
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.HIGH)  # default off (HIGH for active-low relays)

def hysteresis_control(temp, temp_start_compressor=4.5, temp_stop_compressor=3.5):
    """Turn compressor on/off based on set temperatures"""
    if temp > temp_start_compressor:
        return 1
    elif temp < temp_stop_compressor:
        return 0
    else:
        return None

def set_relay_states(states):
    """Turn relays on/off based on received state."""
    for relay, value in states.items():
        pin = RELAY_PINS.get(relay)
        if pin is not None:
            GPIO.output(pin, GPIO.LOW if value == 1 else GPIO.HIGH)

def fetch_relay_states():
    """Request current relay instructions from Flask."""
    try:
        response = requests.get(API_RELAY_URL, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("Received relay state:", data)
            set_relay_states(data)
            return
        else:
            print("Server returned status:", response.status_code)
            set_relay_states({'relay1': 1, 'relay2': 0, 'relay3': 0})
            return
    except requests.RequestException as e:
        print("Error contacting server:", e)

def get_mode():
    """Request control mode"""
    try:
        r = requests.get(API_MODE_URL, timeout=3)
        return r.json().get("mode", "auto"), 0
    except Exception:
        print("Error fetching mode")

    return 'auto', 1

def post_relay_states():
    """Post relay states to the server"""
    try:
        relay_states = {}
        
        for relay, pin in RELAY_PINS.items():
            relay_states[relay] = 1 if GPIO.input(pin) == 0 else 0
        
        relay_states['timestamp'] = int(time.time()) * 1000
        relay_states['mode'] = 'auto'
        r = requests.post(API_RELAY_URL, json=relay_states, timeout=3)
        print("Synced relay states:", r.status_code, relay_states)
        return 1
    except Exception as e:
        print("Failed to sync relay states:", e)
    return 0

def get_config():
    """Fetch compressor control config from the server."""
    try:
        r = requests.get(API_CONFIG_URL, timeout=3)
        if r.status_code == 200:
            data = r.json()
            current_state['config']['temp_start_compressor'] = data.get('temp_start_compressor')
            current_state['config']['temp_stop_compressor'] = data.get('temp_stop_compressor')
            return (
                data.get("temp_start_compressor", 4.5),
                data.get("temp_stop_compressor", 3.5)
            )
    except requests.RequestException as e:
        print("Error fetching config:", e)

    return current_state['config']['temp_start_compressor'], current_state['config']['temp_stop_compressor']  # fallback defaults

def emergency():
    set_relay_states({"relay2": 0, "relay3": 0})

def post_config():
    try:
        requests.post(API_CONFIG_URL, json={'temp_start_compressor': current_state['config']['temp_start_compressor'], 'temp_stop_compressor': current_state['config']['temp_stop_compressor']}, timeout=3)
    except requests.RequestException as e:
        print("Error sending config:", e)

# === Main loop ===
def main():
    global current_state
    print("Starting relay client...")
    setup_gpio()

    if load_state() is not None:
        current_state = load_state()

    last_mode_check = 0
    last_upload = 0
    last_save = 0
    control_mode = 'auto'
    first_connection = True

    try:
        while True:
            temp_dht22, humidity, temp_ds18b20 = read_temp()

            if temp_dht22 and humidity and temp_ds18b20:
                now = time.time()

                if first_connection == True:
                    post_config()
                # Check mode every few seconds
                if now - last_mode_check > CHECK_POLL_INTERVAL:
                    control_mode, connection_check = get_mode()
                    last_mode_check = now
                    first_connection = False

                    if connection_check == 1:
                        emergency()
                        first_connection = True
                    
                    print("Mode:", control_mode)

                # Control logic
                if control_mode == "auto":
                    temp_start, temp_stop = get_config()
                    relay_state = hysteresis_control(temp_ds18b20, temp_start, temp_stop)
                    if relay_state is not None:
                        GPIO.output(RELAY_PINS["relay1"], GPIO.LOW if relay_state == 1 else GPIO.HIGH)
                        post_relay_states()
                else:
                    fetch_relay_states()

                # Send sensor data every minute
                if now - last_upload > UPLOAD_INTERVAL:
                    send_temp(temp_dht22, humidity, temp_ds18b20)
                    last_upload = now

                # Save the current state every 2 mins
                if now - last_save > SAVE_STATE_INTERVAL:
                    save_state(current_state)
                    last_save = now

            time.sleep(SENSOR_READ_INTERVAL)

    except KeyboardInterrupt:
        print("Exiting...")

    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    main()
