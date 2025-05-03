import requests
import urllib3
import logging
from dotenv import load_dotenv
import time
import os
from logging.handlers import TimedRotatingFileHandler

# Disable internal SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables from .env file
load_dotenv()

# Define environment variables
HEALTH_CHECK_URL = os.environ["HEALTH_CHECK_URL"]
OPNSENSE_WIREGUARD_API_URL = os.environ["OPNSENSE_WIREGUARD_API_URL"]
MM_ENABLE = os.environ.get("MM_ENABLE", "false")
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", 60))
LOG_PATH = os.environ.get("LOG_PATH", "/var/log/adow")
LOG_NAME = os.environ.get("LOG_NAME", "adow.log")
LOG_ROTATE = int(os.environ.get("LOG_ROTATE", 7))

# Docker secrets parser
def get_secret(secret_name):
    try:
        with open(f'/run/secrets/{secret_name}', 'r') as secret_file:
            return secret_file.read().strip()
    except FileNotFoundError:
        return None

# Read secrets from Docker
API_KEY = get_secret(os.environ.get("API_KEY_SECRET_NAME", "api-key"))
API_SECRET = get_secret(os.environ.get("API_SECRET_SECRET_NAME", "api-secret"))

# Ensure log directory exists
os.makedirs(LOG_PATH, exist_ok=True)

# Logging configuration
log_file = os.path.join(LOG_PATH, "vpn_health.log")
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# File handler: rotate daily
file_handler = TimedRotatingFileHandler(log_file, when="midnight", interval=1, backupCount=LOG_ROTATE)
file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
file_handler.suffix = "%Y-%m-%d"

# Console handler
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

def send_mattermost_alert(message, color, emoji):
    """Send an alert to Mattermost"""
    payload = {
        "channel": MM_CHANNEL,
        "username": "adow",
        "icon_emoji": emoji,
        "message": message
    }
    response = requests.post(MM_URL, json=payload)
    return response.status_code

def check_server_health():
    try:
        response = requests.get(HEALTH_CHECK_URL, timeout=5, verify=True)
        return response.status_code
    except requests.RequestException as e:
        logging.warning(f"Health check failed: {e}")
        return None

def get_wireguard_status():
    try:
        response = requests.post(
            f"{OPNSENSE_WIREGUARD_API_URL}/service/status",
            headers={"Content-Type": "application/json"},
            auth=(API_KEY, API_SECRET),
            json={},
            verify=False
        )
        if response.ok:
            return response.json().get("status", "unknown")
    except Exception as e:
        logging.error(f"Error fetching WireGuard status: {e}")
    return "unknown"

def enable_wireguard():
    """Activate WireGuard"""
    requests.post(
        f"{OPNSENSE_WIREGUARD_API_URL}/general/set",
        headers={"Content-Type": "application/json"},
        auth=(API_KEY, API_SECRET),
        json={"general": {"enabled": "1"}},
        verify=False
    )
    requests.post(
        f"{OPNSENSE_WIREGUARD_API_URL}/service/reconfigure",
        headers={"Content-Type": "application/json"},
        auth=(API_KEY, API_SECRET),
        json={},
        verify=False
    )
    send_mattermost_alert("WireGuard was activated", "#F35A00", ":warning:")

def disable_wireguard():
    """Deactivate WireGuard"""
    requests.post(
        f"{OPNSENSE_WIREGUARD_API_URL}/general/set",
        headers={"Content-Type": "application/json"},
        auth=(API_KEY, API_SECRET),
        json={"general": {"enabled": "0"}},
        verify=False
    )
    requests.post(
        f"{OPNSENSE_WIREGUARD_API_URL}/service/reconfigure",
        headers={"Content-Type": "application/json"},
        auth=(API_KEY, API_SECRET),
        json={},
        verify=False
    )
    send_mattermost_alert("WireGuard was disabled", "#36A64F", ":white_check_mark:")

def main():
    response_code = check_server_health()

    if response_code != 200:
        logging.warning("Health check failed. Enabling WireGuard...")
        enable_wireguard()
    else:
        logging.info("Health check passed. Checking WireGuard status...")
        wg_status = get_wireguard_status()

        if wg_status in ["unknown", "enabled"]:
            logging.info("WireGuard is active. Disabling WireGuard...")
            disable_wireguard()
        elif wg_status == "disabled":
            logging.info("WireGuard is already disabled.")
        else:
            logging.warning(f"Unknown WireGuard status: {wg_status}")

if __name__ == "__main__":
    init_mattermost_alert = True
    logging.info("====================================")
    logging.info("Automatic Disable OPNsense WireGuard")
    logging.info("====================================")
    logging.info("Monitoring VPN health...")
    logging.info("Starting VPN health check...\n")
    while True:
        if MM_ENABLE == "true":
            if init_mattermost_alert:
                logging.info("Mattermost integration is enabled.\n")
            MM_URL = os.environ["MM_URL"]
            MM_CHANNEL = os.environ["MM_CHANNEL"]
            init_mattermost_alert = False

        try:
            main()
        except Exception as e:
            logging.error(f"Unexpected error: {e}")

        logging.info(f"Sleeping for {CHECK_INTERVAL} seconds...")
        time.sleep(CHECK_INTERVAL)
