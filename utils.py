import logging
import mimetypes
from io import BytesIO
from urllib.parse import unquote

import aiohttp
from pymax import MaxClient, PhotoAttach, VideoAttach, FileAttach, ControlAttach
from pymax import types as max_types
from pymax.types import StickerAttach, AudioAttach, ContactAttach, User, Chat
from pyrogram import Client as PyroClient

from config import TG_CHANNEL_MAIN, SPECIFIC_MAX_GROUPS, TG_CHANNEL_SPECIFIC, SPECIFIC_MAX_CHANNELS, HEADERS

logger = logging.getLogger("MaxTelegramBridge")

async def get_routing_info(max_client: MaxClient, msg: max_types.Message, user: User, chat: Chat):
    """Определяет целевой канал и формирует подпись."""
    chat_id = str(msg.chat_id)

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
        prefix = f"👥 <b>Оригинальный группа: <a href='{chat.link}'>{chat.title}</a></b>\n👤 <b>{first_name}</b>:\n\n"
        if chat_id in SPECIFIC_MAX_GROUPS:
            logger.info(f"{msg.id} from {chat_id} recognized for SPECIFIC chanel")
            target = TG_CHANNEL_SPECIFIC
        else:
            logger.info(f"{msg.id} from {chat_id} recognized for MAIN chanel")
            target = TG_CHANNEL_MAIN
        return target, prefix

    elif chat.type == "CHANNEL":
        logger.info(f"{msg.id} from {chat_id} recognized as channel")
        prefix = f"📢 <b>Оригинальный канал: <a href='{chat.link}'>{chat.title}</a></b>\n\n"
        if chat_id in SPECIFIC_MAX_CHANNELS:
            logger.info(f"{msg.id} from {chat_id} recognized for SPECIFIC chanel")
            target = TG_CHANNEL_SPECIFIC
        else:
            logger.info(f"{msg.id} from {chat_id} recognized for MAIN chanel")
            target = TG_CHANNEL_MAIN
        return target, prefix

    logger.warning(f"{msg.id} from {chat_id} not recognized {chat.type} {chat.title}")
    return TG_CHANNEL_MAIN, "❓ <b>Источник неизвестен</b>\n\n"


from pyrogram.types import InputMediaPhoto, InputMediaVideo, InputMediaDocument
import io

def get_file_name(resp, attach):
    raw_filename = resp.headers.get("X-File-Name")
    content_type = resp.headers.get("Content-Type")

    if raw_filename:
        clean_name = unquote(raw_filename)
    else:
        clean_name = f"file_{attach.file_id}"
    extension = mimetypes.guess_extension(content_type.split(';')[0]) or ".pdf"
    return f"{clean_name}{extension}"

async def prepare_media_item(max_client, chat_id, msg_id, attach, session):
    if isinstance(attach, PhotoAttach):
        logger.info(f"attach in {msg_id} from {chat_id} recognized as PhotoAttach")
        async with session.get(attach.base_url) as resp:
            bio = io.BytesIO(await resp.read())
            bio.name = get_file_name(resp, attach)
            return InputMediaPhoto(bio), bio
    elif isinstance(attach, VideoAttach):
        logger.info(f"attach in {msg_id} from {chat_id} recognized as VideoAttach")
        video = await max_client.get_video_by_id(chat_id, msg_id, attach.video_id)
        async with session.get(video.url) as resp:
            logger.info(video.url)
            logger.info(HEADERS)
            bio = io.BytesIO(await resp.read())
            bio.name = get_file_name(resp, attach)
            return InputMediaVideo(bio), bio
    elif isinstance(attach, FileAttach):
        logger.info(f"attach in {msg_id} from {chat_id} recognized as FileAttach")
        file = await max_client.get_file_by_id(chat_id, msg_id, attach.file_id)
        async with session.get(file.url) as resp:
            bio = io.BytesIO(await resp.read())
            bio.name = get_file_name(resp, attach)
            return InputMediaDocument(bio), bio
    else:
        logger.info(f"attach in {msg_id} from {chat_id} not recognized")
    return None
