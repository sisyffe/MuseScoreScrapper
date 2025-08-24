import logging
import multiprocessing as mp
import os
from typing import Literal

from playwright.sync_api import sync_playwright, Playwright, Browser, Page

from utils import Message
from worker import Worker, Handler

logger = logging.getLogger(__name__)

BrowserTypeAlias = Literal["chromium", "firefox", "webkit"]


class PageManager(Worker):
    METHODS = Worker.METHODS + ["scrap", "fetch_title"]

    def __init__(self, address: str, handler: Handler):
        super().__init__(address, handler)

        self.pw: Playwright | None = None
        self.browser: Browser | None = None
        self.page: Page | None = None

    def init(self, browser: BrowserTypeAlias = "chromium") -> list[Message]:
        if self._is_init:
            raise RuntimeError("Cannot initialize PageManager twice")
        logger.info("Initialising the browser and the page")
        os.system("playwright install")
        self.pw = sync_playwright().start()
        self.browser = getattr(self.pw, browser).launch()
        self.page = self.browser.new_page()
        return super().init()

    def close(self) -> list[Message]:
        if not self._is_init or not self._ready:
            raise RuntimeError("Cannot close PageManager before initialization")
        if self.browser:
            logger.info("Closing the browser")
            self.browser.close()
        if self.pw:
            logger.info("Closing the playwright")
            self.pw.stop()
        return super().close()

    def scrap(self, url: str) -> list[Message]:
        if not self._ready:
            return []
        logger.info("Starting the scrapper")
        self.page.goto(url)
        title = self.page.title()
        print(title)
        return []

    def fetch_title(self, url: str) -> list[Message]:
        if not self._ready:
            return [(self._address, "gui", ("set_title", ("-",), {}))]
        logger.info(f"Fetching selector content for: {url}")
        selector = "#aside-container-unique > div.XkhEk > h1 > span"

        self.page.goto(url)
        self.page.wait_for_load_state("domcontentloaded")

        page_title = self.page.title()
        if page_title.strip() == "Page not found (404) | MuseScore.com":
            logger.warning("Detected 404 page")
            return [(self._address, "gui", ("set_title", ("Page inexistante",), {}))]

        el = self.page.wait_for_selector(selector, state="attached", timeout=5000)
        if not el:
            logger.warning(f"Selector not found: {selector}")
            return [(self._address, "gui", ("set_title", ("Page inexistante",), {}))]

        text = el.text_content()
        return [(self._address, "gui", ("set_title", (text.strip() if text else "Page inexistante",), {}))]


def multiprocess_main(send_queue: mp.Queue, recv_queue: mp.Queue, ppid: int):
    gui_handler = Handler(PageManager, "page", send_queue, recv_queue, ppid)
    gui_handler.listen()
