import requests
import json
import logging

from config import (
    MOBIUS_URL,
    CSE_NAME,
    AE_NAME,
    RAW_DATA_CONTAINER_NAME,
    AI_SERVER_URL
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Use the same headers as the main client, but without Content-Type for this setup
SETUP_HEADERS = {
    "Accept": "application/json",
    "X-M2M-Origin": "S" + AE_NAME, # Use AE's originator ID to create the subscription
    "X-API-KEY": "AWAYXoieop5ncAjTh90YfkHk9eH8Z7Vb",
    "X-AUTH-CUSTOM-LECTURE": "LCT_20250007",
    "X-AUTH-CUSTOM-CREATOR": "dgunamsan",
    "X-M2M-RI": "setup_sub_12345",
    "Content-Type": "application/vnd.onem2m-res+json; ty=23" # ty=23 for Subscription
}

def create_subscription():
    """
    Creates a Subscription resource on the specified raw data container in Mobius.
    This subscription will notify our AI server when new data is added.
    """
    # The container we want to subscribe to
    target_container_url = f"{MOBIUS_URL}/{CSE_NAME}/{AE_NAME}/{RAW_DATA_CONTAINER_NAME}"
    
    # The name for our subscription resource
    subscription_name = "sub_for_ai_server"
    
    # The full URL of the subscription resource itself
    subscription_url = f"{target_container_url}/{subscription_name}"

    # The URL on our AI server that Mobius will send notifications to
    notification_url = f"{AI_SERVER_URL}/notification"

    # The payload to create the subscription
    payload = {
        "m2m:sub": {
            "rn": subscription_name,
            "nu": [notification_url],  # Notification URI: where to send notifications
            "nct": 1,  # Notification Content Type: 1 for modified attributes only, 2 for whole resource
            "enc": {
                "net": [3] # Notification Event and Type: 3 for creation of child resource
            }
        }
    }

    logging.info(f"Attempting to create subscription on: {target_container_url}")
    logging.info(f"Notifications will be sent to: {notification_url}")
    
    try:
        # First, check if subscription already exists to avoid errors
        logging.info(f"Checking if subscription '{subscription_name}' already exists...")
        check_response = requests.get(subscription_url, headers=SETUP_HEADERS)
        if check_response.status_code == 200:
            logging.warning(f"Subscription '{subscription_name}' already exists. No action needed.")
            return

        # If it doesn't exist (404), create it
        logging.info("Subscription does not exist. Creating now...")
        response = requests.post(target_container_url, headers=SETUP_HEADERS, data=json.dumps(payload))
        response.raise_for_status()
        
        logging.info("Successfully created subscription on Mobius!")
        logging.info(f"Status Code: {response.status_code}")
        logging.info(f"Response: {response.text}")

    except requests.exceptions.HTTPError as err:
        logging.error(f"HTTP Error creating subscription: {err}")
        logging.error(f"Response content: {err.response.text}")
    except requests.exceptions.RequestException as err:
        logging.exception(f"A request error occurred: {err}")


if __name__ == "__main__":
    if "YOUR_SERVER_IP" in AI_SERVER_URL:
        logging.error("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        logging.error("!!! ERROR: Please update 'AI_SERVER_URL' in 'config.py' first!")
        logging.error("!!! Replace 'YOUR_SERVER_IP' with the actual IP address of your server.")
        logging.error("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    else:
        create_subscription()
