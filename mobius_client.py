import requests
import json
import logging
from typing import List
from config import MOBIUS_URL, CSE_NAME, AE_NAME, CONTAINER_NAME

logger = logging.getLogger(__name__)

# Headers required for oneM2M communication
MOBIUS_HEADERS = {
    "Accept": "application/json",
    "X-M2M-Origin": "S",  # Set to 'S' as per specification
    "X-API-KEY": "AWAYXoieop5ncAjTh90YfkHk9eH8Z7Vb",
    "X-AUTH-CUSTOM-LECTURE": "LCT_20250007",
    "X-AUTH-CUSTOM-CREATOR": "dgunamsan",
    "X-M2M-RI": "12345",  # Request Identifier, can be a unique ID per request
    "Content-Type": "application/vnd.onem2m-res+json; ty=4" # ty=4 for ContentInstance
}

def create_content_instance(data: dict, labels: List[str] = None):
    """
    Creates a ContentInstance (cin) in the specified oneM2M Container on Mobius.

    Args:
        data (dict): The dictionary containing the data to be stored as the content of the cin.
        labels (List[str], optional): A list of labels to attach to the cin.

    Returns:
        requests.Response: The response object from the Mobius server.
    """
    target_url = f"{MOBIUS_URL}/{CSE_NAME}/{AE_NAME}/{CONTAINER_NAME}"
    
    cin_payload = {
        "con": json.dumps(data)
    }
    if labels:
        cin_payload["lbl"] = labels

    payload = {
        "m2m:cin": cin_payload
    }

    try:
        response = requests.post(target_url, headers=MOBIUS_HEADERS, json=payload)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        logger.info(f"Successfully created ContentInstance at {target_url}. Status: {response.status_code}")
        return response
    except requests.exceptions.HTTPError as err:
        logger.error(f"HTTP Error creating ContentInstance at {target_url}: {err}")
        logger.error(f"Response content: {err.response.text}")
        return None
    except requests.exceptions.RequestException as err:
        logger.exception(f"Request Exception creating ContentInstance at {target_url}: {err}")
        return None

def retrieve_latest_content_instance():
    """
    Retrieves the latest ContentInstance (cin) from the specified oneM2M Container on Mobius.

    Returns:
        dict: The content of the latest cin as a dictionary, or None if an error occurs.
    """
    # To get the latest content instance, append '/latest' to the container URL
    target_url = f"{MOBIUS_URL}/{CSE_NAME}/{AE_NAME}/{CONTAINER_NAME}/latest"
    
    # Headers for retrieving resource (ty not needed)
    headers = MOBIUS_HEADERS.copy()
    headers.pop("Content-Type") # No content type needed for GET requests

    try:
        response = requests.get(target_url, headers=headers)
        response.raise_for_status()
        
        # Parse the oneM2M response to get the content
        response_json = response.json()
        
        # The actual data is in m2m:cin.con
        # It's stored as a JSON string, so we need to parse it again
        content_instance = response_json["m2m:cin"]["con"]
        logger.info(f"Successfully retrieved latest ContentInstance from {target_url}.")
        return json.loads(content_instance)
    except requests.exceptions.HTTPError as err:
        logger.error(f"HTTP Error retrieving latest ContentInstance from {target_url}: {err}")
        logger.error(f"Response content: {err.response.text}")
        return None
    except requests.exceptions.RequestException as err:
        logger.exception(f"Request Exception retrieving latest ContentInstance from {target_url}: {err}")
        return None
    except KeyError as err:
        logger.error(f"KeyError: Could not parse Mobius response for content from {target_url}: {err}")
        return None

def retrieve_all_content_instances(limit: int = None):
    """
    Retrieves all ContentInstances (cin) from the specified oneM2M Container on Mobius.
    Optionally, a limit can be specified to retrieve a certain number of latest instances.

    Args:
        limit (int, optional): The maximum number of latest ContentInstances to retrieve. Defaults to None (all).

    Returns:
        list: A list of dictionaries, where each dictionary is the content of a cin.
              Returns an empty list if no instances are found or an error occurs.
    """
    # To retrieve all content instances, we need to query the container for child resources (ContentInstances)
    # The filter 'ty=4' specifies that we are looking for ContentInstances.
    # The 'rcn=4' specifies retrieve all child resources.
    # The 'fu=1' specifies filter usage.
    # The 'lim' parameter can be used to limit the number of results.
    target_url = f"{MOBIUS_URL}/{CSE_NAME}/{AE_NAME}/{CONTAINER_NAME}?fu=1&ty=4&rcn=4"
    if limit:
        target_url += f"&lim={limit}"

    headers = MOBIUS_HEADERS.copy()
    headers.pop("Content-Type")

    try:
        response = requests.get(target_url, headers=headers)
        response.raise_for_status()
        
        response_json = response.json()
        
        # The response structure for retrieving all children is different
        # It typically contains a list of 'm2m:cin' resources
        content_instances = []
        if "m2m:cnt" in response_json and "cin" in response_json["m2m:cnt"]:
             for cin_data in response_json["m2m:cnt"]["cin"]:
                 if "con" in cin_data:
                     content_instances.append(json.loads(cin_data["con"]))
        elif "m2m:uril" in response_json: # If only URIs are returned, we need to fetch each one
            logger.warning(f"Mobius returned only URIs for {target_url}. Fetching each ContentInstance individually might be slow.")
            # This case means Mobius returned only a list of URIs to the CINS, not the CINS themselves.
            # We would need to iterate and fetch each URI. For simplicity, I'm assuming the direct content return for now.
            # If this is the case, the implementation would need to be more complex.
            # For now, let's assume the direct content return for 'rcn=4' or similar.
            pass # Handle fetching individual CINS if necessary
        else: # For other possible structures
            # Attempt to parse directly if the response is a single m2m:cin or similar
            if "m2m:cin" in response_json:
                # This could happen if the limit is 1 and it behaves like /latest
                content_instances.append(json.loads(response_json["m2m:cin"]["con"]))
        
        logger.info(f"Successfully retrieved {len(content_instances)} ContentInstances from {target_url} (limit={limit}).")
        return content_instances

    except requests.exceptions.HTTPError as err:
        logger.error(f"HTTP Error retrieving ContentInstances from {target_url}: {err}")
        logger.error(f"Response content: {err.response.text}")
        return []
    except requests.exceptions.RequestException as err:
        logger.exception(f"Request Exception retrieving ContentInstances from {target_url}: {err}")
        return []
    except KeyError as err:
        logger.error(f"KeyError: Could not parse Mobius response for content from {target_url}: {err}")
        logger.debug(f"Response JSON: {response_json}") # Print full response for debugging
        return []

