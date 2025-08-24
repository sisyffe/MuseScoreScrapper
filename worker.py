import multiprocessing as mp
import os
import queue
from typing import Type

import settings
from utils import serialize_send, Message, Order


class Worker:
    METHODS = ["init", "close"]

    def __init__(self, address, handler):
        self._address = address
        self._handler = handler
        self._ready = False
        self._is_init = False

    @property
    def address(self):
        return self._address

    @property
    def ready(self):
        return self._ready

    def init(self) -> list[Message]:
        if self._is_init:
            raise RuntimeError("Cannot initialize Worker twice")
        self._ready = True
        self._is_init = True
        return [(self._address, "manager", "finished_init")]

    def close(self) -> list[Message]:
        if not self._is_init or not self._ready:
            raise RuntimeError("Cannot close Worker before initialization")
        self._ready = False
        return [(self._address, "manager", "finished_close")]


class Handler:
    def __init__(self, worker_class: Type[Worker], name: str,
                 send_queue: mp.Queue, recv_queue: mp.Queue, ppid: int):
        self._worker = worker_class(name, self)
        self._send_queue = send_queue
        self._recv_queue = recv_queue
        self._ppid = ppid

        self._running = False

    @property
    def is_ready(self) -> bool:
        return self._worker.ready

    def send_message(self, to: str, what: Order):
        serialize_send(self._worker.address, self._send_queue, to=to, what=what)

    def listen_step(self, *, block: bool = False,
                    timeout_step: float | None = settings.DEFAULT_REFRESH_STEP_TIMEOUT_SEC):
        what = None
        try:
            sender, receiver, what = self._recv_queue.get(block=block, timeout=timeout_step)
        except queue.Empty:
            return
        finally:
            if os.getppid() != self._ppid or what == "_shutdown":
                self._running = False
                return

        func, args, kwargs = what if isinstance(what, tuple) else (what, (), {})
        assert receiver == self._worker.address

        if func not in self._worker.METHODS:
            raise RuntimeError(f"Unknown method {func}")

        result_messages = getattr(self._worker, func)(*args, **kwargs)
        for sender, receiver, what in result_messages:
            serialize_send(sender, self._send_queue, to=receiver, what=what)

    def listen(self, timeout_step: float | None = settings.DEFAULT_REFRESH_STEP_TIMEOUT_SEC):
        self._running = True
        while self._running:
            self.listen_step(block=True, timeout_step=timeout_step)
