import logging
from io import BytesIO

import aiohttp
from pymax import MaxClient, PhotoAttach, VideoAttach, FileAttach, ControlAttach
from pymax import types as max_types
from pymax.types import StickerAttach, AudioAttach, ContactAttach
from pyrogram import Client as PyroClient

from config import TG_CHANNEL_MAIN, SPECIFIC_MAX_GROUPS, TG_CHANNEL_SPECIFIC, SPECIFIC_MAX_CHANNELS

logger = logging.getLogger("MaxTelegramBridge")

async def get_routing_info(max_client: MaxClient, msg: max_types.Message):
    """Определяет целевой канал и формирует подпись."""
    chat_id = str(msg.chat_id)
    chat = await max_client.get_chat(msg.chat_id)
    sender = msg.sender

    # Определяем префикс в зависимости от типа чата
    if chat.type == "DIALOG":
        prefix = f"👤 <b>ЛС от: {sender}</b>\n\n"
        return TG_CHANNEL_MAIN, prefix

    elif chat.type == "CHAT":
        prefix = f"👥 <b>Группа: {chat.title}</b>\n👤 <b>{sender}</b>:\n\n"
        target = TG_CHANNEL_SPECIFIC if chat_id in SPECIFIC_MAX_GROUPS else TG_CHANNEL_MAIN
        return target, prefix

    elif chat.type == "channel":
        prefix = f"📢 <b>Канал: {chat.title}</b>\n\n"
        target = TG_CHANNEL_SPECIFIC if chat_id in SPECIFIC_MAX_CHANNELS else TG_CHANNEL_MAIN
        return target, prefix

    return TG_CHANNEL_MAIN, "❓ <b>Источник неизвестен</b>\n\n"


from pyrogram.types import InputMediaPhoto, InputMediaVideo, InputMediaDocument
import io


async def prepare_media_item(max_client, chat_id, msg_id, attach, session):
    if isinstance(attach, PhotoAttach):
        async with session.get(attach.base_url) as resp:
            bio = io.BytesIO(await resp.read())
            bio.name = f"photo_{attach.photo_id}.jpg"
            return InputMediaPhoto(bio)

    elif isinstance(attach, VideoAttach):
        video = await max_client.get_video_by_id(chat_id, msg_id, attach.video_id)
        async with session.get(video.url) as resp:
            bio = io.BytesIO(await resp.read())
            bio.name = resp.headers.get("X-File-Name", "video.mp4")
            return InputMediaVideo(bio)

    elif isinstance(attach, FileAttach):
        file = await max_client.get_file_by_id(chat_id, msg_id, attach.file_id)
        async with session.get(file.url) as resp:
            bio = io.BytesIO(await resp.read())
            bio.name = resp.headers.get("X-File-Name", "file.pdf")
            return InputMediaDocument(bio)

    return None
