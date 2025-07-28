import logging

from playwright.async_api import Playwright, Browser, Page


logger = logging.getLogger(__name__)


class PageManager:
    def __init__(self, pw):
        self.pw: Playwright = pw
        self.browser: Browser | None = None
        self.page: Page | None = None

    async def init(self):
        logger.info("Initialising the browser")
        self.browser = await self.pw.chromium.launch()

    async def close(self):
        logger.info("Closing the browser")
        await self.browser.close()

    async def main(self):
        await self.init()
        await self.run()
        await self.close()

    async def run(self):
        logger.info("Starting the scrapper")
        self.page = await self.browser.new_page()
        await self.page.goto("https://playwright.dev/python/docs/library")
        print(await self.page.title())

