import logging
from typing import Literal

from playwright.async_api import Playwright, Browser, Page


logger = logging.getLogger(__name__)


class PageManager:
    def __init__(self, pw):
        self.pw: Playwright = pw
        self.browser: Browser | None = None
        self.page: Page | None = None

    async def init(self, browser: Literal["chromium", "firefox", "webkit"] = "chromium"):
        logger.info("Initialising the browser and the page")
        self.browser = await getattr(self.pw, browser).launch()
        self.page = await self.browser.new_page()

    async def close(self):
        if self.browser:
            logger.info("Closing the browser")
            await self.browser.close()

    async def run(self, page: str):
        logger.info("Starting the scrapper")
        await self.page.goto(page)
        print(await self.page.title())

