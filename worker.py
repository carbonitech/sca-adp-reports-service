"""worker setup for heroku job queueing"""
import os
import redis
from dotenv import load_dotenv
from rq import Worker, Queue, Connection

load_dotenv()

listen = ["high", "default", "low"]

redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')

conn = redis.from_url(redis_url)

if __name__ == "__main__":
    with Connection(conn):
        worker = Worker(map(Queue,listen))
        worker.work()