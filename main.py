import logging
import runpy

import settings
from handler_manager import HandlerManager

logging.basicConfig(**settings.LOGGING_CONFIG)
runpy.run_path(".venv/bin/activate_this.py")

logger = logging.getLogger(__name__)
handler_manager: HandlerManager


def main():
    global handler_manager
    logger.info("Starting the application")

    try:
        handler_manager = HandlerManager()
        handler_manager.run()
    except Exception as e:
        logger.critical(f"An error occurred (exiting) : {str(e)}")
        raise

if __name__ == "__main__":
    main()
