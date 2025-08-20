import logging
from typing import Literal
from concurrent.futures import ThreadPoolExecutor, Future
import asyncio

from playwright.sync_api import sync_playwright, Playwright, Browser, Page

logger = logging.getLogger(__name__)

class PageManager:
    def __init__(self):
        self.running = False
        self.pw: Playwright | None = None
        self.browser: Browser | None = None
        self.page: Page | None = None

    def init(self, browser: Literal["chromium", "firefox", "webkit"] = "chromium"):
        logger.info("Initialising the browser and the page")
        self.pw = sync_playwright().start()
        self.browser = getattr(self.pw, browser).launch()
        self.page = self.browser.new_page()
        self.running = True
        logger.info("Browser and page initialised")

    def close(self):
        if not self.running:
            return
        if self.browser:
            logger.info("Closing the browser")
            self.browser.close()
        if self.pw:
            logger.info("Closing the playwright")
            self.pw.stop()
        self.running = False

    def run(self, page: str):
        if not self.running:
            logger.warning("run() called while PageManager is not initialised")
            return
        logger.info("Starting the scrapper")
        self.page.goto(page)
        title = self.page.title()
        print(title)

    def get_title(self, url: str) -> str:
        if not self.running:
            logger.warning("get_title() called while PageManager is not initialised")
            return ""

        logger.info(f"Fetching selector content for: {url}")
        selector = "#aside-container-unique > div.XkhEk > h1 > span"

        try:
            self.page.goto(url)
            self.page.wait_for_load_state("domcontentloaded")

            page_title = self.page.title()
            if page_title.strip() == "Page not found (404) | MuseScore.com":
                logger.info("Detected 404 page")
                return "Page inexistante"

            el = self.page.wait_for_selector(selector, state="attached", timeout=10000)
            if not el:
                logger.warning(f"Selector not found: {selector}")
                return "Page inexistante"

            text = el.text_content()
            return text.strip() if text else "Page inexistante"

        except Exception as e:
            logger.exception(f"Error while fetching selector content: {e}")
            return "Page inexistante"


class PageManagerWorker:
    """
    Proxy thread-safe: exécute toutes les méthodes de PageManager
    dans un seul thread dédié (toujours le même).
    Offre des variantes async (awaitables) et nowait (non-bloquantes).
    """
    def __init__(self, default_browser: Literal["chromium", "firefox", "webkit"] = "chromium"):
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="page-manager")
        self._pm = PageManager()
        self._default_browser = default_browser
        self._closed = False
        self._init_future: Future | None = None

    def _submit(self, fn, *args, **kwargs) -> Future:
        if self._closed and fn is not self._pm.close:
            raise RuntimeError("PageManagerWorker is already closed")
        return self._executor.submit(fn, *args, **kwargs)

    async def init(self, browser: Literal["chromium", "firefox", "webkit"] | None = None):
        if self._init_future is None:
            self._init_future = self._submit(self._pm.init, browser or self._default_browser)
        await asyncio.wrap_future(self._init_future)

    def init_nowait(self, browser: Literal["chromium", "firefox", "webkit"] | None = None) -> Future:
        self._init_future = self._submit(self._pm.init, browser or self._default_browser)
        return self._init_future

    async def run(self, url: str):
        if self._init_future is not None and not self._init_future.done():
            await asyncio.wrap_future(self._init_future)
        fut = self._submit(self._pm.run, url)
        await asyncio.wrap_future(fut)

    def run_nowait(self, url: str) -> Future:
        return self._submit(self._pm.run, url)

    async def fetch_title(self, url: str) -> str:
        if self._init_future is not None and not self._init_future.done():
            await asyncio.wrap_future(self._init_future)
        fut = self._submit(self._pm.get_title, url)
        return await asyncio.wrap_future(fut)

    def fetch_title_nowait(self, url: str) -> Future:
        return self._submit(self._pm.get_title, url)

    async def close(self):
        try:
            fut = self._submit(self._pm.close)
            await asyncio.wrap_future(fut)
        finally:
            self._closed = True
            self._executor.shutdown(wait=False, cancel_futures=True)

    def close_nowait(self) -> Future:
        fut = self._submit(self._pm.close)
        self._closed = True
        self._executor.shutdown(wait=False, cancel_futures=True)
        return fut