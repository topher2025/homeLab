import logging
import asyncio
import aiohttp
from logging.handlers import RotatingFileHandler


class AsyncAPILogHandler(logging.Handler):
    """Async handler that sends logs to a remote API."""
    def __init__(self, api_url, loop=None):
        super().__init__()
        self.api_url = api_url
        self.loop = loop or asyncio.get_event_loop()
        self.session = aiohttp.ClientSession()

    async def _send(self, record):
        if self.session is None:
            return

        payload = {
            "timestamp": record.asctim,
            "threadname": record.threadname,
            "level": record.levelname,
            "message": self.format(record),
            "logger": record.name,
        }
        try:
            await self.session.post(self.api_url, json=payload)
        except Exception:
            pass  # avoid recursive logging

    def emit(self, record):
        if self.session is None:
            return

        asyncio.ensure_future(self._send(record), loop=self.loop)


def get_logger(name="mylogger", url="http://192.168.0.3:8000/api/logs/router/"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # --- Rotating file handler (size-based) ---
    # Example: 1 MB max, keep 3 backups
    file_handler = RotatingFileHandler(
        "app.log",
        maxBytes=1_000_000,   # adjust as needed
        backupCount=3
    )
    formatter = logging.Formatter(
        "%(asctime)s [%(threadName)s] %(levelname)s: %(message)s"

    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # --- Async API handler ---
    api_handler = AsyncAPILogHandler(url)
    api_handler.setFormatter(formatter)
    logger.addHandler(api_handler)

    return logger


async def shutdown_logger(logger):
    """Call this on shutdown to close aiohttp session."""
    for handler in logger.handlers:
        if isinstance(handler, AsyncAPILogHandler) and handler.session is not None:
            await handler.session.close()
