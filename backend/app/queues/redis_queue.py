from redis import Redis
from rq import Queue
from app.core.config import get_settings

settings = get_settings()


def get_redis_connection() -> Redis:
    return Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=0,
        decode_responses=False,
    )


def get_invoice_queue() -> Queue:
    redis_conn = get_redis_connection()
    return Queue("invoices", connection=redis_conn)
