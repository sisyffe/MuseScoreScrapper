import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
from typing import Literal

from playwright.sync_api import sync_playwright, Playwright, Browser, Page

logger = logging.getLogger(__name__)

BrowserTypeAlias = Literal["chromium", "firefox", "webkit"]


class PageManager:
    def __init__(self):
        self.pw: Playwright | None = None
        self.browser: Browser | None = None
        self.page: Page | None = None

        self._ready: asyncio.Event = asyncio.Event()

    def init(self, browser: BrowserTypeAlias = "chromium"):
        if self._ready.is_set():
            return
        logger.info("Initialising the browser and the page")
        self.pw = sync_playwright().start()
        self.browser = getattr(self.pw, browser).launch()
        self.page = self.browser.new_page()
        self._ready.set()
        logger.info("Browser and page initialised")

    def close(self):
        if not self._ready.is_set():
            return
        if self.browser:
            logger.info("Closing the browser")
            self.browser.close()
        if self.pw:
            logger.info("Closing the playwright")
            self.pw.stop()
        self._ready.clear()

    def run(self, url: str):
        if not self._ready.is_set():
            return
        logger.info("Starting the scrapper")
        self.page.goto(url)
        title = self.page.title()
        print(title)

    def fetch_title(self, url: str) -> str:
        if not self._ready.is_set():
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
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="PageManagerWorker")
        self._delay_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="PageManagerWorkerDelay")
        self._lock: asyncio.Lock = asyncio.Lock()

        self._init_future: asyncio.Future | None = None

    def _submit(self, func, *args, executor: ThreadPoolExecutor | None = None, **kwargs) -> asyncio.Future:
        return (executor or self._executor).submit(func, *args, **kwargs)

    def init_nowait(self, browser: BrowserTypeAlias = "chromium") -> asyncio.Future:
        self._init_future = self._submit(super().init, browser)
        return self._init_future

    def run_nowait(self, url: str) -> asyncio.Future:
        return self._submit(super().run, url)

    def fetch_title_nowait(self, url: str) -> asyncio.Future:
        return self._submit(super().fetch_title, url)

    def close_nowait(self) -> asyncio.Future:
        return self._submit(super().close)

    # Variantes synchrones (bloquantes), mais exécutées sur le thread dédié
    def init(self, browser: BrowserTypeAlias = "chromium"):
        return self.init_nowait(browser).result()

    def run(self, url: str):
        return self.run_nowait(url).result()

    def fetch_title(self, url: str) -> str:
        return self.fetch_title_nowait(url).result()

    def close(self):
        return self.close_nowait().result()

    # Variantes asynchrones (asyncio)
    async def init_async(self, browser: BrowserTypeAlias = "chromium"):
        return await asyncio.wrap_future(self.init_nowait(browser))

    async def run_async(self, url: str):
        return await asyncio.wrap_future(self.run_nowait(url))

    async def fetch_title_async(self, url: str) -> str:
        return await asyncio.wrap_future(self.fetch_title_nowait(url))

    async def close_async(self):
        return await asyncio.wrap_future(self.close_nowait())

