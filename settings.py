import logging
from typing import Literal

BROWSER: Literal["chromium", "firefox", "webkit"] = "chromium"
LOGGING_CONFIG = {
    "level": logging.INFO,
    "format": '%(asctime)s - [%(levelname)s] %(filename)s - %(message)s',
    "datefmt": '%Y-%m-%d %H:%M:%S'
}
ENTRY_PLACEHOLDER = "Entrez l'URL ici (https://musescore.com/...)"
WINDOW_GEOMETRY = "520x160"
