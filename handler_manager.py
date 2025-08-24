import logging
import multiprocessing as mp
import multiprocessing.connection
import os

from utils import serialize_send, Order
from gui_manager import multiprocess_main as gui_worker
from page_manager import multiprocess_main as page_worker


logger = logging.getLogger(__name__)

class HandlerManager:
    ADDRESS = "manager"
    WORKERS = {"gui": gui_worker, "page": page_worker}

    def __init__(self):
        self._workers: dict[str, tuple[mp.Queue, mp.Process]] = {}
        self._recv_queue = mp.Queue()
        self._running_count = 0

    def start_all_workers(self):
        for name, worker_func in self.WORKERS.items():
            send_queue = mp.Queue()
            proc = mp.Process(target=worker_func, kwargs={"send_queue": self._recv_queue,
                                                          "recv_queue": send_queue,
                                                          "ppid": os.getpid()})
            self._workers[name] = send_queue, proc
            proc.start()
            self._running_count += 1

    def init_all_workers(self):
        for name, (send_queue, proc) in self._workers.items():
            serialize_send(self.ADDRESS, send_queue, to=name, what="init")

    def close_all_workers(self):
        for name, (send_queue, proc) in self._workers.items():
            serialize_send(self.ADDRESS, send_queue, to=name, what="close")

    def wait_all_workers(self):
        for name, (send_queue, proc) in self._workers.items():
            proc.join(timeout=1.0)
            if proc.is_alive():
                proc.terminate()
                proc.join()
            send_queue.close()
        self._recv_queue.close()

    def handle_message(self, sender: str, what: Order) -> None:
        if what == "finished_init":
            logger.info(f"Finished initialization: {sender}")
            if sender == "gui":
                serialize_send(self.ADDRESS, self._workers["gui"][0], to="gui", what="mainloop")
        elif what == "finished_close":
            logger.info(f"Finished closing: {sender}")
            serialize_send(self.ADDRESS, self._workers[sender][0], to=sender, what="_shutdown")
            self._running_count -= 1
        elif what == "request_shutdown":
            logger.info(f"Received shutdown request: {sender}")
            self.close_all_workers()

    def listen_all_workers(self):
        self.init_all_workers()

        while self._running_count > 0:
            message = self._recv_queue.get()
            sender, receiver, what = message

            if receiver == self.ADDRESS:
                self.handle_message(sender, what)
            elif receiver in self._workers:
                send_queue, proc = self._workers[receiver]
                serialize_send(sender, send_queue, to=receiver, what=what)
            else:
                raise RuntimeError(f"Worker {receiver} not found")

    def run(self):
        self.start_all_workers()
        self.listen_all_workers()
        self.wait_all_workers()
