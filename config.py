# Mobius oneM2M Platform Configuration
# ------------------------------------
# This file contains the configuration for connecting to the Mobius oneM2M platform.

# The base URL of the Mobius oneM2M platform
MOBIUS_URL = "https://onem2m.iotcoss.ac.kr"

# The name of the Common Service Entity (CSE) - typically "Mobius"
CSE_NAME = "Mobius"

# The name of your Application Entity (AE) as created on the Mobius platform
AE_NAME = "ae_Namsan"

# The name of the Container to store the noise event data, created under your AE
CONTAINER_NAME = "cnt_noise"

# The name of the Container where Arduinos will post the RAW sensor data
RAW_DATA_CONTAINER_NAME = "cnt_raw" # Placeholder name

# The publicly accessible URL of this AI server for Mobius to send notifications to.
# Replace 'YOUR_SERVER_IP' with the actual public or local IP address of the machine running this server.
AI_SERVER_URL = "http://192.168.0.115:8080"


# AI Model Configuration
# ----------------------
# Threshold for vibration peak counting (g)
VIBRATION_THRESHOLD = 2.0

# Default sampling rate for audio preprocessing (Hz)
# This is a default and can be overridden by dynamic values from the payload.
DEFAULT_SAMPLING_RATE = 22050

# Number of MFCCs to extract for audio features
MFCC_COUNT = 20