# Mobius oneM2M Platform Configuration
# ------------------------------------
# This file contains the configuration for connecting to the Mobius oneM2M platform.

# The base URL of the Mobius oneM2M platform
MOBIUS_URL = "https://onem2m.iotcoss.ac.kr"

# The name of the Common Service Entity (CSE) - typically "Mobius"
CSE_NAME = "Mobius"

# The name of your Application Entity (AE) as created on the Mobius platform
AE_NAME = "ae_Namsan"

# --- Container Names ---
# 1. INPUT: Arduino posts Raw Data (Vibration/Sound JSON) here
CNT_RAW = "cnt_raw_sensor" 

# 2. OUTPUT 1: AI posts Noise Level/Grade (Green, Yellow, Red) here for Arduino/Web
CNT_STATUS = "cnt_status"

# 3. OUTPUT 2: AI posts Noise Type (Footstep, Furniture, etc.) here for Arduino/Web
CNT_NOISE = "cnt_noise"

# 4. INPUT: Apology acknowledgements
CNT_APOLOGY = "cnt_apology"

# Backward compatibility aliases (for existing code)
RAW_DATA_CONTAINER_NAME = CNT_RAW
CONTAINER_NAME = CNT_NOISE # Default output container for now
APOLOGY_CONTAINER_NAME = CNT_APOLOGY

# The publicly accessible URL of this AI server for Mobius to send notifications to.
# Replace 'YOUR_SERVER_IP' with the actual public or local IP address of the machine running this server.
AI_SERVER_URL = "https://8ce841b24568.ngrok-free.app"

# AI Model Configuration
# ----------------------
# Threshold for vibration peak counting (g)
VIBRATION_THRESHOLD = 2.0

# Default sampling rate for audio preprocessing (Hz)
# This is a default and can be overridden by dynamic values from the payload.
DEFAULT_SAMPLING_RATE = 22050

# Number of MFCCs to extract for audio features
MFCC_COUNT = 20

# Network Configuration
# ---------------------
# Timeout for network requests (seconds)
REQUEST_TIMEOUT = 10

# MOCK DATA MODE Configuration
# -----------------------------
# Set to True to enable mock data generation for frontend development
# when the Mobius server is unavailable.
# Set to False to use actual Mobius notifications.
MOCK_DATA_MODE = False