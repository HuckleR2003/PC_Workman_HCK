"""ui.bg - work off the UI thread without touching Tk from it (2026-11-21).

The rule: a worker thread never calls Tk and never holds a Tk object.
  * Tk called from a worker (widget.after(0, ...), widget.config(...)) raises
    "main thread is not in main loop" whenever the main loop is not the one
    pumping. The error was swallowed and the page never filled in: the
    Startup Manager stayed on "Scanning…" (2026-11-20).
  * A worker holding the last reference to a widget frees the Tk
    interpreter from that thread when the window closes, which aborts the
    whole process with Tcl_AsyncDelete (tests in November 2026).

So the work runs on a thread with plain data only, and the window asks for
the result with widget.after() on its own thread:

    run(widget, work, done)          work() on a thread (no Tk inside, no
                                     widgets in its closure); done(result)
                                     on the UI thread, only if widget lives
    box = Mailbox(); watch(widget, box, on_item)
                                     a thread (a daemon's status callback)
                                     box.put(x); on_item(x) runs on the UI
                                     thread, in order, while widget lives
"""
from __future__ import annotations

import collections
import threading
from typing import Any, Callable, Optional

POLL_MS = 100


def _alive(widget) -> bool:
    try:
        return bool(widget.winfo_exists())
    except Exception:
        return False


class _Result:
    __slots__ = ("done", "value", "error")

    def __init__(self):
        self.done = False
        self.value = None
        self.error: Optional[BaseException] = None


def _work_on_thread(box: _Result, work: Callable[[], Any]) -> None:
    try:
        box.value = work()
    except BaseException as e:          # reported on the UI thread
        box.error = e
    box.done = True


def run(widget, work: Callable[[], Any], done: Optional[Callable[[Any], None]] = None,
        fail: Optional[Callable[[BaseException], None]] = None,
        poll_ms: int = POLL_MS, name: str = "ui-bg") -> _Result:
    """work() on a worker thread; done(result) or fail(error) on the UI
    thread once it ends, unless the widget is gone by then. `work` must not
    touch Tk or hold widgets: pass it plain values."""
    box = _Result()
    threading.Thread(target=_work_on_thread, args=(box, work), daemon=True, name=name).start()

    def _poll():
        if not _alive(widget):
            return
        if not box.done:
            widget.after(poll_ms, _poll)
            return
        try:
            if box.error is not None:
                if fail is not None:
                    fail(box.error)
                else:
                    print(f"[ui.bg] {name}: {box.error}")
            elif done is not None:
                done(box.value)
        except Exception as e:
            print(f"[ui.bg] {name} done: {e}")
    try:
        widget.after(poll_ms, _poll)
    except Exception:
        pass
    return box


def later(widget, seconds: float, fn: Callable[[], None]) -> None:
    """fn() on the UI thread after a pause, if the widget still lives (for
    "show DONE, then put the button back" without a sleeping thread)."""
    def _go():
        if _alive(widget):
            try:
                fn()
            except Exception:
                pass
    try:
        widget.after(int(seconds * 1000), _go)
    except Exception:
        pass


class Mailbox:
    """Items put from any thread, taken on the UI thread. Holds no Tk."""

    def __init__(self, maxlen: int = 200):
        self._q = collections.deque(maxlen=maxlen)
        self.closed = False

    def put(self, item) -> None:
        if not self.closed:
            self._q.append(item)

    def take_all(self) -> list:
        out = []
        while self._q:
            try:
                out.append(self._q.popleft())
            except IndexError:
                break
        return out


def watch(widget, box: Mailbox, on_item: Callable[[Any], None],
          every_ms: int = 250, on_close: Optional[Callable[[], None]] = None) -> None:
    """Deliver the mailbox's items to on_item on the UI thread while the
    widget lives; when it is gone, close the box and call on_close (e.g.
    to unregister a listener).

    Closing hangs on <Destroy>: Tkinter deletes a widget's pending after()
    callbacks with it, so a poll alone would never see the widget go."""
    state = {"closed": False}

    def _close(e=None):
        if e is not None and getattr(e, "widget", widget) is not widget:
            return                       # a child was destroyed, not the widget
        if state["closed"]:
            return
        state["closed"] = True
        box.closed = True
        if on_close is not None:
            try:
                on_close()
            except Exception:
                pass

    def _poll():
        if state["closed"]:
            return
        if not _alive(widget):
            _close()
            return
        for item in box.take_all():
            try:
                on_item(item)
            except Exception:
                pass
        widget.after(every_ms, _poll)
    try:
        widget.bind("<Destroy>", _close, add="+")
        widget.after(every_ms, _poll)
    except Exception:
        _close()


_POSTED = Mailbox(maxlen=1000)
_PUMP = {"root": None}


def post(fn: Callable[[], None]) -> None:
    """Ask the UI thread to run fn() soon, from any thread (a chat answer
    applying a fan profile, a watcher showing a toast). Needs install(root);
    tests call drain()."""
    _POSTED.put(fn)


def drain() -> int:
    """Run what was posted. UI thread only. Returns how many ran."""
    n = 0
    for fn in _POSTED.take_all():
        n += 1
        try:
            fn()
        except Exception as e:
            print(f"[ui.bg] posted call: {e}")
    return n


def install(root, every_ms: int = 50) -> None:
    """Pump post()ed calls on the UI thread (the main window calls this)."""
    if _PUMP["root"] is root:
        return
    _PUMP["root"] = root

    def _pump():
        if _PUMP["root"] is not root or not _alive(root):
            return
        drain()
        root.after(every_ms, _pump)
    root.after(every_ms, _pump)


def listener(box: Mailbox) -> Callable[[Any], None]:
    """A callback for a daemon that only fills the mailbox (holds no Tk)."""
    def _put(item, _b=box):
        _b.put(item)
    return _put
