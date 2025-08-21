import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
import os
from typing import Literal

from playwright.sync_api import sync_playwright, Playwright, Browser, Page

logger = logging.getLogger(__name__)

BrowserTypeAlias = Literal["chromium", "firefox", "webkit"]

class PageManager:
    def __init__(self):
        self.ready = False
        self.pw: Playwright | None = None
        self.browser: Browser | None = None
        self.page: Page | None = None

    def _init(self, browser: BrowserTypeAlias = "chromium"):
        logger.info("Initialising the browser and the page")
        os.system("playwright install")
        self.pw = sync_playwright().start()
        self.browser = getattr(self.pw, browser).launch()
        self.page = self.browser.new_page()
        self.ready = True
        logger.info("Browser and page initialised")

    def close(self):
        if not self.ready:
            return
        if self.browser:
            logger.info("Closing the browser")
            self.browser.close()
        if self.pw:
            logger.info("Closing the playwright")
            self.pw.stop()
        self.ready = False

    def _run(self, url: str):
        if not self.ready:
            logger.warning("run() called while PageManager is not initialised")
            return
        logger.info("Starting the scrapper")
        self.page.goto(url)
        title = self.page.title()
        print(title)

    def _fetch_title(self, url: str) -> str:
        if not self.ready:
            logger.warning("get_title() called while PageManager is not initialised")
            return "-"

        logger.info(f"Fetching selector content for: {url}")
        selector = "#aside-container-unique > div.XkhEk > h1 > span"

        self.page.goto(url)
        self.page.wait_for_load_state("domcontentloaded")

        page_title = self.page.title()
        if page_title.strip() == "Page not found (404) | MuseScore.com":
            logger.warning("Detected 404 page")
            return "Page inexistante"

        el = self.page.wait_for_selector(selector, state="attached", timeout=5000)
        if not el:
            logger.warning(f"Selector not found: {selector}")
            return "Page inexistante"

        text = el.text_content()
        return text.strip() if text else "Page inexistante"


class PageManagerWorker(PageManager):
    def __init__(self):
        super().__init__()
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._init_future: asyncio.Future | None = None
        self._init_event: asyncio.Event | None = None

    def _submit(self, func, *args, **kwargs) -> asyncio.Future:
        loop = asyncio.get_running_loop()
        return loop.run_in_executor(
            self._executor,
            lambda: func(*args, **kwargs)
        )

    def init_nowait(self, browser: BrowserTypeAlias = "chromium") -> asyncio.Event:
        self._init_future = self._executor.submit(self._init, browser)
        self._init_event = asyncio.Event()
        self._init_future.add_done_callback(lambda _: self._init_event.set())
        return self._init_event

    async def run_async(self, url: str) -> str:
        await asyncio.shield(self._init_future)
        return await self._submit(self._run, url)

    def run_nowait(self, url: str) -> asyncio.Event:
        def run_wait():
            self._init_event.wait()
            return self._run(url)
        future = self._executor.submit(run_wait)
        event = asyncio.Event()
        future.add_done_callback(lambda _: event.set())
        return event

    async def fetch_title_async(self, url: str) -> str:
        print(self._init_future)
        print(self._init_event)
        await asyncio.shield(self._init_future)
        return await self._submit(self._fetch_title, url)
