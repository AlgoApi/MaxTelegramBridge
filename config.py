# --- Конфигурация ---
import os

CURRENT_MAX_USERID = int(os.getenv("CURRENT_MAX_USERID", "0"))
MAX_PHONE = os.getenv("MAX_PHONE", "")

TG_API_ID = int(os.getenv("TG_API_ID", "0"))
TG_API_HASH = os.getenv("TG_API_HASH", "")
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "")

TG_CHANNEL_MAIN = int(os.getenv("TG_CHANNEL_MAIN", "0"))
TG_CHANNEL_SPECIFIC = int(os.getenv("TG_CHANNEL_SPECIFIC", "0"))

SPECIFIC_MAX_GROUPS = os.getenv("SPECIFIC_MAX_GROUPS", "").split(",")
SPECIFIC_MAX_CHANNELS = os.getenv("SPECIFIC_MAX_CHANNELS", "").split(",")