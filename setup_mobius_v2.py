import requests
import json
import logging
from config import MOBIUS_URL, CSE_NAME, AE_NAME, CNT_RAW, CNT_STATUS, CNT_NOISE, CNT_APOLOGY, REQUEST_TIMEOUT

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

HEADERS = {
    "Accept": "application/json",
    "X-M2M-Origin": "S" + AE_NAME,
    "X-API-KEY": "AWAYXoieop5ncAjTh90YfkHk9eH8Z7Vb",
    "X-AUTH-CUSTOM-LECTURE": "LCT_20250007",
    "X-AUTH-CUSTOM-CREATOR": "dgunamsan",
    "X-M2M-RI": "setup_v2_12345",
    "Content-Type": "application/vnd.onem2m-res+json; ty=3" # ty=3 for Container
}

def create_container(container_name):
    target_url = f"{MOBIUS_URL}/{CSE_NAME}/{AE_NAME}"
    
    payload = {
        "m2m:cnt": {
            "rn": container_name,
            "mni": 100 # Max number of instances
        }
    }

    try:
        logging.info(f"Checking/Creating Container: {container_name}...")
        # Check if exists
        check_url = f"{target_url}/{container_name}"
        res = requests.get(check_url, headers={"Accept": "application/json", "X-M2M-Origin": "S", "X-M2M-RI": "check"}, timeout=REQUEST_TIMEOUT)
        
        if res.status_code == 200:
            logging.info(f"✅ Container '{container_name}' already exists.")
            return

        # Create
        response = requests.post(target_url, headers=HEADERS, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        logging.info(f"🎉 Successfully created container '{container_name}'.")

    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Failed to create container '{container_name}': {e}")

if __name__ == "__main__":
    containers = [CNT_RAW, CNT_STATUS, CNT_NOISE, CNT_APOLOGY]
    logging.info(f"Starting Mobius Container Setup for: {containers}")
    
    for cnt in containers:
        create_container(cnt)
    
    logging.info("All setup tasks completed.")