import asyncio
import io
import logging
from typing import List

import sys
from pymax import types as max_types
from pymax.static.enum import MessageStatus
from pymax.types import User, Names
from pyrogram import Client as PyroClient, filters as tg_filters
from pyrogram.handlers import MessageHandler as TG_MessageHandler
from pyrogram.types import InputMediaPhoto, InputMediaVideo, InputMediaDocument

from config import CURRENT_MAX_USERID, SUPPORTED_ATTACHES, TG_CHANNEL_MAIN, TG_CHANNEL_SPECIFIC, TG_API_ID, TG_API_HASH, \
    TG_BOT_TOKEN, TG_ADMIN_USERID
from init_clients import max_client
from redis_db import msg_map
from utils import get_routing_info, download_attaches

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("MaxTelegramBridge")

tg_app: PyroClient
SHUTDOWN_INTERVAL = 3 * 60 * 60

class GracefulShutdown(Exception):
    pass

async def shutdown_timer():
    await asyncio.sleep(SHUTDOWN_INTERVAL)
    raise GracefulShutdown()

async def whoami(client: PyroClient, message):
    chat = message.chat
    text = (
        f"**CHAT INFO**\n"
        f"ID: `{chat.id}`\n"
        f"Type: `{chat.type}`\n"
        f"Title: {chat.title or 'N/A'}\n"
        f"Reply ID: {message.reply_to_message_id or 'None'}"
    )
    await message.reply_text(text)

    if message.video:
        await message.reply_text(f"🎬 `video_id`: `{message.video.file_id}`")
    if message.photo:
        await message.reply_text(f"🖼 `photo_id`: `{message.photo.file_id}`")
    if message.animation:
        await message.reply_text(f"🎞 `gif_id`: `{message.animation.file_id}`")

    try:
        await tg_app.get_chat(TG_CHANNEL_MAIN)
    except Exception as e:
        logger.error(f"Cannot resolve TG_CHANNEL_MAIN Try send random message to chanel: {e}")
    try:
        await tg_app.get_chat(TG_CHANNEL_SPECIFIC)
    except Exception as e:
        logger.error(f"Cannot resolve TG_CHANNEL_SPECIFIC Try send random message to chanel: {e}")


from pyrogram.handlers import MessageHandler
from pyrogram import filters


async def fetch_history(client: PyroClient, message):
    cmd_args = message.command
    if len(cmd_args) < 3:
        logger.error("Usage: /fetch <max_chat_id> <limit>")
        return

    try:
        max_chat_id = int(cmd_args[1])
        limit = int(cmd_args[2])
        logger.info(f"fetching last {limit} message from {max_chat_id}")

        history = await max_client.fetch_history(max_chat_id, backward=limit)

        if not history:
            logger.info("messages not found or max_chat_id invalid")
            return

        for msg in history:
            msg.chat_id = max_chat_id
            await on_new_message(msg)
            await asyncio.sleep(2)

        logger.info(f"forwarded {len(history)} messages")

    except ValueError as e:
        logger.error(f"invalid max_chat_id {e}")
    except Exception as e:
        logger.error(f"error on fetch: {e}")

@max_client.on_message()
async def on_new_message(message: max_types.Message):
    chat_obj = await max_client.get_chat(message.chat_id)
    if message.sender:
        msg_user = await max_client.get_user(message.sender)
    else:
        msg_user = User(0, 0, message.chat_id, [Names(chat_obj.title, None, None, None)])
    logger.info(f"got message {message.id} from {msg_user.id} in {message.chat_id}")
    if msg_user.id == CURRENT_MAX_USERID:
        logger.info("this message is message from owner, skip...")
        return
    target_channel, prefix = await get_routing_info(max_client, message, msg_user, chat_obj)

    if message.status == MessageStatus.REMOVED:
        logger.info(f"get mappings for {message.chat_id} in {message.id} for delete")
        tg_ids = await msg_map.get_mapping(message.chat_id, message.id)
        if tg_ids:
            await tg_app.delete_messages(target_channel, tg_ids)
            logger.info(f"Message {message.id} in {message.chat_id} deleted in telegram")
        return

    if message.status == MessageStatus.EDITED:
        logger.info(f"get mappings for {message.chat_id} in {message.id} for edit")
        tg_ids = await msg_map.get_mapping(message.chat_id, message.id)
        if tg_ids:
            new_text = f"{prefix}{message.text or ''}"
            try:
                await tg_app.edit_message_text(target_channel, tg_ids[0], new_text)
            except Exception:
                await tg_app.edit_message_caption(target_channel, tg_ids[0], new_text)
            logger.info(f"Message {message.id} in {message.chat_id} redacted in telegram")
        return

    full_text = f"{prefix}{message.text or ''}"
    sent_messages = []

    if message.attaches and any(isinstance(a, SUPPORTED_ATTACHES) for a in message.attaches):
        media_list_bio: List[io.BytesIO]
        media_list: List[InputMediaPhoto,InputMediaVideo, InputMediaDocument]
        voice_list: List[io.BytesIO]

        media_list_bio, media_list, voice_list = await download_attaches(max_client, message.chat_id, message.id, message.attaches)

        if media_list:
            logger.info(f"detected media in message {message.id} in {message.chat_id}")
            logger.debug(media_list)
            try:
                for i in range(0, len(media_list), 10):
                    media_batch = media_list[i:i + 10]
                    try:
                        media_list[0].caption = full_text
                        res = await tg_app.send_media_group(target_channel, media_batch)
                        sent_messages.extend([m.id for m in res])
                        logger.info(f"message send_media_group to telegram {sent_messages}")
                    except Exception as e:
                        logger.error(f"Error send media {media_batch}: {e}")
                        logger.info("Attempting fallback to InputMediaDocument...")
                        try:
                            doc_media = []
                            for m in media_batch:
                                doc_media.append(InputMediaDocument(m.media, caption=m.caption))

                            res = await tg_app.send_media_group(target_channel, doc_media)
                            sent_messages.extend([m.id for m in res])
                            logger.info(f"message send_media_group all documents to telegram {sent_messages}")
                        except Exception as e_inner:
                            logger.error(f"Fallback failed: {e_inner}")
            finally:
                for bio in media_list_bio:
                    if not bio.closed:
                        bio.close()
        if voice_list:
            for audio in voice_list:
                try:
                    res = await tg_app.send_voice(
                        chat_id=target_channel,
                        voice=audio,
                        caption=full_text
                    )
                    sent_messages.append(res.id)
                    logger.info(f"message send_voice to telegram {res.id}")
                    full_text = ""
                except Exception as e:
                    logger.error(f"Error send voice message: {e}")
                finally:
                    if not audio.closed:
                        audio.close()
    else:
        try:
            res = await tg_app.send_message(target_channel, full_text, disable_web_page_preview=True)
            sent_messages = [res.id]
            logger.info(f"message send to telegram {res.id}")
        except Exception as e:
            logger.error(f"Error message send message: {e}")

    if sent_messages:
        logger.info(f"save message mappings")
        await msg_map.save_mapping(message.chat_id, message.id, sent_messages)


@max_client.on_start
async def on_start() -> None:
    logger.info(f"Max client started. Your ID: {max_client.me.id}")
    try:
        await tg_app.get_chat(TG_CHANNEL_MAIN)
    except Exception as e:
        logger.error(f"Cannot resolve TG_CHANNEL_MAIN, Try send random message to chanel: {e}")
    try:
        await tg_app.get_chat(TG_CHANNEL_SPECIFIC)
    except Exception as e:
        logger.error(f"Cannot resolve TG_CHANNEL_SPECIFIC, Try send random message to chanel: {e} ")


async def start_bridge():
    global tg_app
    tg_app = PyroClient("sessions/tg_session", api_id=TG_API_ID, api_hash=TG_API_HASH, bot_token=TG_BOT_TOKEN)

    try:
        tg_app.add_handler(TG_MessageHandler(whoami, tg_filters.command("whoami")))
        tg_app.add_handler(MessageHandler(fetch_history, filters.command("fetch") & filters.user(TG_ADMIN_USERID)))
        await tg_app.start()
    except Exception as e:
        logger.error(f"Error in telegram bot: {e}")
        return  
    logger.info("telegram bot started.")

    shutdown_task = asyncio.create_task(shutdown_timer())

    try:
        await asyncio.wait(
            [
                asyncio.create_task(max_client.start()),
                shutdown_task
            ],
            return_when=asyncio.FIRST_COMPLETED
        )
    except GracefulShutdown:
        logger.info("rebooting")
    except Exception as e:
        logger.error(f"Error in Max UserBot: {e}")
    finally:
        if not shutdown_task.done():
            shutdown_task.cancel()
            try:
                await shutdown_task
            except asyncio.CancelledError:
                pass
        logger.info("Try to close telegram bot safely")
        await tg_app.stop()
        await asyncio.sleep(3)


if __name__ == "__main__":
    try:
        asyncio.run(start_bridge())
    except KeyboardInterrupt:
        pass
    except GracefulShutdown:
        pass
