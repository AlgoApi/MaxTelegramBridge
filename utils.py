import io
import logging
from typing import List, Union
from urllib.parse import unquote

import aiohttp
import filetype

from urllib.parse import urlparse, parse_qs
from pymax import MaxClient, PhotoAttach, VideoAttach, FileAttach
from pymax import types as max_types
from pymax.types import User, Chat, AudioAttach
from pyrogram.types import InputMediaPhoto, InputMediaVideo, InputMediaDocument

from config import TG_CHANNEL_MAIN, SPECIFIC_MAX_GROUPS, TG_CHANNEL_SPECIFIC, SPECIFIC_MAX_CHANNELS

logger = logging.getLogger("MaxTelegramBridge")

def get_headers_for_max(url: str):
    parsed_url = urlparse(url)
    params = parse_qs(parsed_url.query)
    src_ag = params.get('srcAg', [''])[0].upper()

    if any(x in src_ag for x in ["SAFARI", "MACOS"]):
        ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15"

    elif any(x in src_ag for x in ["UBUNTU", "FEDORA", "DEBIAN"]):
        ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

    else:
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

    return {
        "User-Agent": ua,
        "Accept": "*/*",
        "Connection": "keep-alive",
        "Accept-Language": "ru-RU,ru;q=0.9"
    }

async def download_attaches(max_client: MaxClient, chat_id:int, msg_id:int, attaches):
    media_list_bio: List[io.BytesIO] = []
    media_list: List[Union[InputMediaPhoto, InputMediaVideo, InputMediaDocument]] = []
    voice_list: List[io.BytesIO] = []
    async with aiohttp.ClientSession() as session:
        for attach in attaches:
            if isinstance(attach, AudioAttach):
                try:
                    url = attach.url
                    current_headers = get_headers_for_max(url)
                    async with session.get(url, headers=current_headers) as resp:
                        resp.raise_for_status()
                        bio = io.BytesIO(await resp.read())

                        bio.name = f"voice{attach.audio_id}.ogg"
                        voice_list.append(bio)
                except Exception as e:
                    logger.error(f"error download voice: {e}")
            else:
                media = await prepare_media_item(max_client, chat_id, msg_id, attach, session)
                if media:
                    input_media, bio = media
                    media_list.append(input_media)
                    media_list_bio.append(bio)
    return media_list_bio, media_list, voice_list


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
        prefix = f"👥 <b>Оригинальная группа: <a href='{chat.link}'>{chat.title}</a></b>\n👤 <b>{first_name}</b>:\n\n"
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

def get_file_name(resp, file_bytes, file_id, fallback_extension:str):
    raw_name = resp.headers.get("X-File-Name", f"file_{file_id}")
    clean_name = ""
    
    clean_name = unquote(raw_name)
    
    kind = filetype.guess(file_bytes)
    if kind:
        logger.info(f"guess {file_id} extension: {kind.extension}")
        ext = f".{kind.extension}"
    else:
        logger.info("cannot guess extension for {file_id}")
        ext = fallback_extension

    if ext == ".webp":
        ext = ".jpg"
    return f"{clean_name}{ext}"

async def prepare_media_item(max_client, chat_id, msg_id, attach, session):
    if isinstance(attach, PhotoAttach):
        logger.info(f"attach in {msg_id} from {chat_id} recognized as PhotoAttach")
        async with session.get(attach.base_url) as resp:
            file_bytes = await resp.read()
            bio = io.BytesIO(file_bytes)
            bio.name = get_file_name(resp, file_bytes, attach.photo_id, ".jpg")
            return InputMediaPhoto(bio), bio
    elif isinstance(attach, VideoAttach):
        logger.info(f"attach in {msg_id} from {chat_id} recognized as VideoAttach")
        video = await max_client.get_video_by_id(chat_id, msg_id, attach.video_id)
        async with session.get(video.url) as resp:
            file_bytes = await resp.read()
            bio = io.BytesIO(file_bytes)
            bio.name = get_file_name(resp, file_bytes, attach.video_id, ".mp4")
            return InputMediaVideo(bio), bio
    elif isinstance(attach, FileAttach):
        logger.info(f"attach in {msg_id} from {chat_id} recognized as FileAttach")
        file = await max_client.get_file_by_id(chat_id, msg_id, attach.file_id)
        async with session.get(file.url) as resp:
            file_bytes = await resp.read()
            bio = io.BytesIO(file_bytes)
            bio.name = get_file_name(resp, file_bytes, attach.file_id, ".pdf")
            return InputMediaDocument(bio), bio
    else:
        logger.info(f"attach in {msg_id} from {chat_id} not recognized")
    return None
