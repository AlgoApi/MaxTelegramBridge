import logging
import pymax.mixins as mixins
import qrcode

from config import TG_API_ID, TG_BOT_TOKEN, TG_API_HASH

logger = logging.getLogger("MaxTelegramBridge")

def _logged_print_qr(self, qr_link: str):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.ERROR_CORRECT_L,
        box_size=1,
        border=1,
    )
    qr.add_data(qr_link)
    qr.make(fit=True)

    logger.info(f"\n--- QR CODE для авторизации ---")
    qr.print_ascii()
    logger.info("\n--- АЛЬТЕРНАТИВНЫЙ ВАРИАНТ ---")
    logger.info("Если QR-код выше отображается криво и не сканируется, скопируйте ссылку ниже:")
    logger.info(f"{qr_link}")
    logger.info("И вставьте её в любой генератор QR-кодов (например, qrcoder.ru), после чего отсканируйте.")

mixins.AuthMixin._print_qr = _logged_print_qr

from pymax import MaxClient
max_client: MaxClient

max_client = MaxClient(
    phone="+79001234567",
    work_dir="./sessions",
    send_fake_telemetry=False,
    reconnect=True,
    reconnect_delay=5.0,
)