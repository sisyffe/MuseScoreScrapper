import asyncio
import logging
import os
import runpy

from playwright.async_api import async_playwright, Playwright

import settings
from page_manager import PageManager
from gui_manager import GUIManager


logging.basicConfig(**settings.LOGGING_CONFIG)
runpy.run_path(".venv/bin/activate_this.py")
os.system("playwright install")


logger = logging.getLogger(__name__)
page_manager: PageManager
gui_manager: GUIManager


async def run_app():
    global page_manager, gui_manager
    logger.info("Starting the application")
    pw: Playwright | None = None

    async def run_steps():
        global page_manager, gui_manager
        nonlocal pw

        pw = await async_playwright().start()
        page_manager = PageManager(pw)
        gui_manager = GUIManager()

        gui_manager.init()
        page_url, save_path = gui_manager.run_sync()
        if not page_url or not save_path:
            return

        await page_manager.init(settings.BROWSER)
        await page_manager.run(page_url)

    try:
        await run_steps()
    except Exception as e:
        logger.critical(f"An error occurred (exiting) : {str(e)}")
        raise
    finally:
        gui_manager.close()
        await page_manager.close()
        if pw:
            await pw.stop()


if __name__ == "__main__":
    asyncio.run(run_app())