"""Generator-based Qt controller: yield a callable to run blocking work off-thread."""

import inspect
import logging
from functools import wraps

from PyQt5 import sip
from PyQt5.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal
from PyQt5.QtWidgets import QMessageBox

log = logging.getLogger(__name__)
_POOL = None
_TASKS = set()


def worker_pool() -> QThreadPool:
    global _POOL
    if _POOL is None:
        _POOL = QThreadPool()
        _POOL.setMaxThreadCount(1)  # Preserve order across messenger and admin requests.
    return _POOL


def _widget_closed(widget) -> bool:
    while widget is not None:
        if sip.isdeleted(widget) or getattr(widget, "_closing", False):
            return True
        widget = widget.parent()
    return False


class Signals(QObject):
    done = pyqtSignal(object, object)


class Task(QRunnable):
    def __init__(self, operation):
        super().__init__()
        self.operation = operation
        self.signals = Signals()  # Created on GUI thread; results are delivered there.

    def run(self):
        try:
            result, failure = self.operation(), None
        except Exception as exc:
            log.exception("Background operation failed")
            result, failure = None, exc
        self.signals.done.emit(result, failure)


def background(method):
    """Keep widget code on the GUI thread; run only yielded callables in the pool.

    Coalesce repeated timer ticks and button clicks while that widget operation
    is pending. A bounded global backlog prevents slow sockets accumulating work.
    """

    accepts_arguments = len(inspect.signature(method).parameters) > 1

    @wraps(method)
    def start(self, *args, **kwargs):
        if _widget_closed(self):
            return
        # QPushButton.clicked emits a checked bool. Qt normally drops it for
        # zero-argument slots; this variadic decorator must do so explicitly.
        if not accepts_arguments and len(args) == 1 and type(args[0]) is bool:
            args = ()
        pending = getattr(self, "_pending_operations", None)
        if pending is None:
            pending = self._pending_operations = set()
        key = method.__name__
        if key in pending or len(_TASKS) >= 16:
            return
        generator = method(self, *args, **kwargs)
        if not inspect.isgenerator(generator):
            return generator
        pending.add(key)

        def advance(result=None, failure=None):
            if _widget_closed(self):
                pending.discard(key)
                generator.close()
                return
            try:
                operation = generator.throw(failure) if failure else generator.send(result)
            except StopIteration:
                pending.discard(key)
                return
            except Exception:
                pending.discard(key)
                log.exception("UI operation failed")
                QMessageBox.warning(self, "Request failed", "The operation could not be completed.")
                return
            task = Task(operation)
            _TASKS.add(task)

            def completed(value, problem):
                _TASKS.discard(task)
                advance(value, problem)

            task.signals.done.connect(completed)
            worker_pool().start(task)

        advance()

    return start
