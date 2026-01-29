import requests
import json
import time
import random
from datetime import datetime

# The URL of your FastAPI server's predict endpoint
URL = "http://localhost:8000/predict"

def generate_dummy_data():
    """Generates a dummy data payload in the NewPayload format."""
    
    # Simulate some vibration data with occasional peaks
    vibration_data = [random.uniform(0.5, 1.5) for _ in range(10)]
    if random.random() < 0.3: # 30% chance of a significant peak
        peak_index = random.randint(0, 9)
        vibration_data[peak_index] = random.uniform(2.5, 4.0)

    # Simulate some sound feature data
    sound_features = [random.random() for _ in range(20)]

    payload = {
        "house_id": "Below_301",
        "timestamp": datetime.now().isoformat() + "Z",
        "meta": {
            "sampling_rate": "22050Hz",
            "vibration_unit": "g",
            "sound_unit": "dB"
        },
        "payload": {
            "vibration": {
                "z": vibration_data
            },
            "sound_features": sound_features,
            "raw_max_decibel": random.uniform(50.0, 85.0)
        }
    }
    return payload

def send_request(data):
    """Sends a POST request to the server with the given data."""
    try:
        response = requests.post(URL, headers={"Content-Type": "application/json"}, data=json.dumps(data))
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx) 
        
        print("Request successful!")
        print(f"Status Code: {response.status_code}")
        print("Response JSON:")
        print(json.dumps(response.json(), indent=2))

    except requests.exceptions.HTTPError as errh:
        print(f"Http Error: {errh}")
        print(f"Response Content: {errh.response.text}")
    except requests.exceptions.ConnectionError as errc:
        print(f"Error Connecting: {errc}")
    except requests.exceptions.Timeout as errt:
        print(f"Timeout Error: {errt}")
    except requests.exceptions.RequestException as err:
        print(f"Oops: Something Else: {err}")

if __name__ == "__main__":
    print("--- Sending a test request to the AI Server ---")
    dummy_data = generate_dummy_data()
    
    print("\nGenerated Payload:")
    print(json.dumps(dummy_data, indent=2))
    
    print(f"\nSending POST request to {URL}...")
    send_request(dummy_data)
    
    print("\n--- Test complete ---")
    print("Check your running Vue.js dashboard to see the real-time update via WebSocket.")
