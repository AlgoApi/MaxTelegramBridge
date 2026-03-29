# --- Конфигурация ---
import os

from pymax import PhotoAttach, VideoAttach, FileAttach
from pymax.types import AudioAttach

CURRENT_MAX_USERID = int(os.getenv("CURRENT_MAX_USERID", "0"))
MAX_PHONE = os.getenv("MAX_PHONE", "")

TG_API_ID = int(os.getenv("TG_API_ID", "0"))
TG_API_HASH = os.getenv("TG_API_HASH", "")
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "")

TG_CHANNEL_MAIN = int(os.getenv("TG_CHANNEL_MAIN", "0"))
TG_CHANNEL_SPECIFIC = int(os.getenv("TG_CHANNEL_SPECIFIC", "0"))

SPECIFIC_MAX_GROUPS = os.getenv("SPECIFIC_MAX_GROUPS", "").split(",")
SPECIFIC_MAX_CHANNELS = os.getenv("SPECIFIC_MAX_CHANNELS", "").split(",")

SUPPORTED_ATTACHES = (PhotoAttach, VideoAttach, FileAttach, AudioAttach)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
    "Accept": "video/webm,video/ogg,video/*;q=0.9,application/ogg;q=0.7,audio/*;q=0.6,*/*;q=0.5",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive"
}