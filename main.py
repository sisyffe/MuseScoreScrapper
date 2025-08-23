import asyncio
import logging
import os
import runpy

import settings
from gui_manager import GUIManager

logging.basicConfig(**settings.LOGGING_CONFIG)
runpy.run_path(".venv/bin/activate_this.py")
os.system("playwright install")

logger = logging.getLogger(__name__)
gui_manager: GUIManager


def run_app():
    global gui_manager

    gui_manager = GUIManager()
    gui_manager.init()
    gui_manager.run()

def main():
    logger.info("Starting the application")

    try:
        run_app()
    except Exception as e:
        logger.critical(f"An error occurred (exiting) : {str(e)}")
        raise
    finally:
        gui_manager.close()

if __name__ == "__main__":
    main()