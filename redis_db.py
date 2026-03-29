import os

import redis.asyncio as redis

class RedisMapping:
    def __init__(self, host='localhost', port=6379, db=0):
        self.client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self.ttl = 86400  # 24 часа

    async def save_mapping(self, max_chat_id, max_msg_id, tg_msg_ids: list):
        key = f"msg_map:{max_chat_id}:{max_msg_id}"
        # Сохраняем ID сообщений Telegram через запятую
        await self.client.set(key, ",".join(map(str, tg_msg_ids)), ex=self.ttl)

    async def get_mapping(self, max_chat_id, max_msg_id):
        key = f"msg_map:{max_chat_id}:{max_msg_id}"
        data = await self.client.get(key)
        if data:
            return list(map(int, data.split(",")))
        return None

# Инициализируем в главном файле
msg_map = RedisMapping(host=os.getenv("REDIS_HOST", "localhost"))