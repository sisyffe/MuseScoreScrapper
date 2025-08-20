import logging
from typing import Literal

from PySide6.QtCore import QStandardPaths

BROWSER: Literal["chromium", "firefox", "webkit"] = "chromium"
LOGGING_CONFIG = {
    "level": logging.INFO,
    "format": '%(asctime)s - [%(levelname)s] %(filename)s - %(message)s',
    "datefmt": '%Y-%m-%d %H:%M:%S'
}
ENTRY_PLACEHOLDER = "Entrez ou collez l'URL ici (https://musescore.com/...)"
WINDOW_GEOMETRY: tuple[int, int] = (560, 260)
FETCH_TITLE_DEBOUNCE_MS: int = 500
DEFAULT_AUTO_TITLE_MODE: bool = True
DEFAULT_FOLDER_LOCATION = QStandardPaths.StandardLocation.DesktopLocation
DEFAULT_FILE_NAME = "partition.pdf"

