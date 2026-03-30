import redis.asyncio as redis
from config import REDIS_HOST, REDIS_PASSWORD


class RedisMapping:
    def __init__(self, password, host='localhost', port=6379, db=0):
        self.client = redis.Redis(host=host, port=port, db=db, decode_responses=True, password=password)
        self.ttl = 86400  # 24 часа

    async def save_mapping(self, max_chat_id, max_msg_id, tg_msg_ids: list):
        key = f"msg_map:{max_chat_id}:{max_msg_id}"
        await self.client.set(key, ",".join(map(str, tg_msg_ids)), ex=self.ttl)

    async def get_mapping(self, max_chat_id, max_msg_id):
        key = f"msg_map:{max_chat_id}:{max_msg_id}"
        data = await self.client.get(key)
        if data:
            return list(map(int, data.split(",")))
        return None

msg_map = RedisMapping(host=REDIS_HOST, password=REDIS_PASSWORD)