"""Server defaults; command-line arguments override deployment settings."""

from pathlib import Path

from shared.constants import DEFAULT_HOST, DEFAULT_PORT

HOST = DEFAULT_HOST
PORT = DEFAULT_PORT
DATABASE_PATH = str(Path(__file__).resolve().parents[1] / "corporate_messenger.db")
MAX_CONNECTIONS = 32
MAX_LOGIN_ATTEMPTS = 5
BLOCK_TIME = 300
MAX_REQUESTS_PER_SECOND = 30
MAX_AUTH_TRACKED_IPS = 4096
AUTH_HASH_CONCURRENCY = 2
