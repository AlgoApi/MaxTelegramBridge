import asyncio
import logging

import aiohttp
from pymax import types as max_types
from pymax.static.enum import MessageStatus

from config import CURRENT_MAX_USERID
from init_clients import max_client, tg_app
from pymax import MaxClient

from redis_db import msg_map
from utils import get_routing_info, prepare_media_item

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("MaxTelegramBridge")


@max_client.on_message()
async def on_new_message(message: max_types.Message):
    msg_user = await max_client.get_user(message.sender)
    if msg_user.id == CURRENT_MAX_USERID:
        return
    target_channel, prefix = await get_routing_info(max_client, message, msg_user)

    if message.status == MessageStatus.REMOVED:
        tg_ids = await msg_map.get_mapping(message.chat_id, message.id)
        if tg_ids:
            await tg_app.delete_messages(target_channel, tg_ids)
            logger.info(f"Сообщение {message.id} удалено в TG")
        return

    if message.status == MessageStatus.EDITED:
        tg_ids = await msg_map.get_mapping(message.chat_id, message.id)
        if tg_ids:
            new_text = f"{prefix}{message.text or ''}"
            try:
                await tg_app.edit_message_text(target_channel, tg_ids[0], new_text)
            except Exception:
                await tg_app.edit_message_caption(target_channel, tg_ids[0], new_text)
        return

    full_text = f"{prefix}{message.text or ''}"
    sent_messages = []

    if message.attaches:
        media_list = []
        async with aiohttp.ClientSession() as session:
            for attach in message.attaches:
                media = await prepare_media_item(max_client, message.chat_id, message.id, attach, session)
                if media:
                    media_list.append(media)

        if media_list:
            media_list[0].caption = full_text
            res = await tg_app.send_media_group(target_channel, media_list[:10])
            sent_messages = [m.id for m in res]
    else:
        # Просто текстовое сообщение
        res = await tg_app.send_message(target_channel, full_text, disable_web_page_preview=True)
        sent_messages = [res.id]

    # Сохраняем связку в Redis для будущего Edit/Delete
    if sent_messages:
        await msg_map.save_mapping(message.chat_id, message.id, sent_messages)


@max_client.on_start
async def on_start() -> None:
    print(f"Клиент запущен. Ваш ID: {max_client.me.id}")

    # Получение истории
    history = await max_client.fetch_history(chat_id=257786917)
    print("Последние сообщения из чата 257786917:")
    for m in history:
        print(f"- {m.text}")

async def start_bridge():
    await tg_app.start()
    logger.info("Telegram клиент запущен.")

    try:
        await max_client.start()
    except Exception as e:
        logger.error(f"Ошибка в работе моста: {e}")
    finally:
        await tg_app.stop()
        pass


if __name__ == "__main__":
    try:
        asyncio.run(start_bridge())
    except KeyboardInterrupt:
        pass