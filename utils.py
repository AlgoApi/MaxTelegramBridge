import logging
from io import BytesIO

import aiohttp
from pymax import MaxClient, PhotoAttach, VideoAttach, FileAttach, ControlAttach
from pymax import types as max_types
from pymax.types import StickerAttach, AudioAttach, ContactAttach, User
from pyrogram import Client as PyroClient

from config import TG_CHANNEL_MAIN, SPECIFIC_MAX_GROUPS, TG_CHANNEL_SPECIFIC, SPECIFIC_MAX_CHANNELS

logger = logging.getLogger("MaxTelegramBridge")

async def get_routing_info(max_client: MaxClient, msg: max_types.Message, user: User):
    """Определяет целевой канал и формирует подпись."""
    chat_id = str(msg.chat_id)
    chat = await max_client.get_chat(msg.chat_id)

    # Определяем префикс в зависимости от типа чата
    if chat.type == "DIALOG":
        logger.info(f"{msg.id} from {chat_id} recognized as DIALOG")
        first_name = None
        if user.names:
            first_name = user.names[0].name
        prefix = f"👤 <b>ЛС от {first_name}:</b>\n\n"
        return TG_CHANNEL_MAIN, prefix

    elif chat.type == "CHAT":
        logger.info(f"{msg.id} from {chat_id} recognized as CHAT")
        first_name = None
        if user.names:
            first_name = user.names[0].name
        prefix = f"👥 <b>Группа: {chat.title}</b>\n👤 <b>{first_name}</b>:\n\n"
        target = TG_CHANNEL_SPECIFIC if chat_id in SPECIFIC_MAX_GROUPS else TG_CHANNEL_MAIN
        return target, prefix

    elif chat.type == "channel":
        logger.info(f"{msg.id} from {chat_id} recognized as channel")
        prefix = f"📢 <b>Канал: {chat.title}</b>\n\n"
        target = TG_CHANNEL_SPECIFIC if chat_id in SPECIFIC_MAX_CHANNELS else TG_CHANNEL_MAIN
        return target, prefix

    logger.warning(f"{msg.id} from {chat_id} not recognized")
    return TG_CHANNEL_MAIN, "❓ <b>Источник неизвестен</b>\n\n"


from pyrogram.types import InputMediaPhoto, InputMediaVideo, InputMediaDocument
import io


async def prepare_media_item(max_client, chat_id, msg_id, attach, session):
    if isinstance(attach, PhotoAttach):
        logger.info(f"attach in {msg_id} from {chat_id} recognized as PhotoAttach")
        async with session.get(attach.base_url) as resp:
            bio = io.BytesIO(await resp.read())
            bio.name = f"photo_{attach.photo_id}.jpg"
            return InputMediaPhoto(bio), bio
    elif isinstance(attach, VideoAttach):
        logger.info(f"attach in {msg_id} from {chat_id} recognized as VideoAttach")
        video = await max_client.get_video_by_id(chat_id, msg_id, attach.video_id)
        async with session.get(video.url) as resp:
            bio = io.BytesIO(await resp.read())
            bio.name = resp.headers.get("X-File-Name", f"video{attach.video_id}.mp4")
            return InputMediaVideo(bio), bio
    elif isinstance(attach, FileAttach):
        logger.info(f"attach in {msg_id} from {chat_id} recognized as FileAttach")
        file = await max_client.get_file_by_id(chat_id, msg_id, attach.file_id)
        async with session.get(file.url) as resp:
            bio = io.BytesIO(await resp.read())
            bio.name = resp.headers.get("X-File-Name", f"file{attach.file_id}.pdf")
            return InputMediaDocument(bio), bio
    else:
        logger.info(f"attach in {msg_id} from {chat_id} not recognized")
    return None
