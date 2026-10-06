from config import settings
import redis 

redis_client = redis.from_url(settings.redis_url, decode_responses = True)
