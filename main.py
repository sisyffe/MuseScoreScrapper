import asyncio
import logging
import os
import runpy

from playwright.async_api import async_playwright
from page_manager import PageManager


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] %(filename)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
runpy.run_path(".venv/bin/activate_this.py")
os.system("playwright install")


logger = logging.getLogger(__name__)
page_manager: PageManager


async def run_app():
    global page_manager
    logger.info("Starting the application")
    try:
        async with async_playwright() as pw:
            page_manager = PageManager(pw)
            logger.info("PageManager initialised")
            await page_manager.main()
    except Exception as e:
        logger.critical(f"An error occurred (exiting : {str(e)}")
        raise
    finally:
        logger.info("Closing the application")


if __name__ == "__main__":
    asyncio.run(run_app())