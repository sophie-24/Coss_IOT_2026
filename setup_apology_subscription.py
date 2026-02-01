import requests
import json
import logging

from config import (
    MOBIUS_URL,
    CSE_NAME,
    AE_NAME,
    APOLOGY_CONTAINER_NAME,
    AI_SERVER_URL
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SETUP_HEADERS = {
    "Accept": "application/json",
    "X-M2M-Origin": "S" + AE_NAME,
    "X-API-KEY": "AWAYXoieop5ncAjTh90YfkHk9eH8Z7Vb",
    "X-AUTH-CUSTOM-LECTURE": "LCT_20250007",
    "X-AUTH-CUSTOM-CREATOR": "dgunamsan",
    "X-M2M-RI": "setup_sub_apology",
    "Content-Type": "application/vnd.onem2m-res+json; ty=23"
}

def create_apology_subscription():
    """
    Creates a Subscription resource on the apology container in Mobius.
    """
    target_container_url = f"{MOBIUS_URL}/{CSE_NAME}/{AE_NAME}/{APOLOGY_CONTAINER_NAME}"
    subscription_name = "sub_for_apology"
    subscription_url = f"{target_container_url}/{subscription_name}"
    
    # We point to a specific endpoint for apologies
    notification_url = f"{AI_SERVER_URL}/apology_notification"

    payload = {
        "m2m:sub": {
            "rn": subscription_name,
            "nu": [notification_url],
            "nct": 1,
            "enc": {
                "net": [3] # Creation of child resource
            }
        }
    }

    logging.info(f"Attempting to create subscription on: {target_container_url}")
    
    try:
        logging.info(f"Checking if subscription '{subscription_name}' already exists...")
        check_response = requests.get(subscription_url, headers=SETUP_HEADERS)
        if check_response.status_code == 200:
            logging.warning(f"Subscription '{subscription_name}' already exists.")
            return

        logging.info("Subscription does not exist. Creating now...")
        response = requests.post(target_container_url, headers=SETUP_HEADERS, data=json.dumps(payload))
        response.raise_for_status()
        
        logging.info("Successfully created apology subscription!")

    except requests.exceptions.HTTPError as err:
        logging.error(f"HTTP Error: {err}")
        logging.error(f"Response: {err.response.text}")
    except Exception as err:
        logging.exception(f"Error: {err}")

if __name__ == "__main__":
    create_apology_subscription()
