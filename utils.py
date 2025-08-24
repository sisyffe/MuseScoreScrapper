import multiprocessing as mp

Order = tuple[str, tuple, dict] | str
Message = tuple[str, str, Order]


def serialize_send(sender: str, send_queue: mp.Queue, /, *, to: str,
                   what: Order) -> None:
    send_queue.put((sender, to, what))
