import logging
from typing import Literal

BROWSER: Literal["chromium", "firefox", "webkit"] = "chromium"
LOGGING_CONFIG = {
    "level": logging.INFO,
    "format": '%(asctime)s - [%(levelname)s] %(filename)s - %(message)s',
    "datefmt": '%Y-%m-%d %H:%M:%S'
}
ENTRY_PLACEHOLDER = "Entrez ou collez l'URL ici (https://musescore.com/...)"
WINDOW_GEOMETRY: tuple[int, int] = (560, 260)
