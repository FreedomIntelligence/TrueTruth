"""Thread-safe print() capture for SSE log streaming.

Each worker thread registers its own log callback via thread-local storage.
The global sys.stdout is monkey-patched once with a dispatching writer that
routes each line to the correct thread's callback.  This is safe for multiple
concurrent workflow requests.
"""

import sys
import threading
import io
from typing import Callable, Optional

_thread_local = threading.local()
_original_stdout = sys.stdout
_patched = False
_patch_lock = threading.Lock()


class _DispatchingWriter(io.TextIOBase):
    """Replacement for sys.stdout that routes writes to per-thread callbacks."""

    def write(self, s: str) -> int:
        # Always echo to the real stdout
        _original_stdout.write(s)
        _original_stdout.flush()

        # Route to per-thread callback if installed
        callback: Optional[Callable] = getattr(_thread_local, "log_callback", None)
        if callback is None:
            return len(s)

        buf_attr = "_log_buf"
        buf: str = getattr(_thread_local, buf_attr, "")
        buf += s
        while "\n" in buf:
            line, buf = buf.split("\n", 1)
            if line.strip():
                agent: str = getattr(_thread_local, "current_agent", "system")
                callback(line, agent)
        setattr(_thread_local, buf_attr, buf)
        return len(s)

    def flush(self):
        _original_stdout.flush()


def install_global_patch():
    """Replace sys.stdout once with the dispatching writer (idempotent)."""
    global _patched
    with _patch_lock:
        if not _patched:
            sys.stdout = _DispatchingWriter()
            _patched = True


def register_thread_callback(callback: Callable[[str, str], None]):
    """Register a (line, agent) callback for the current thread."""
    install_global_patch()
    _thread_local.log_callback = callback
    _thread_local._log_buf = ""
    _thread_local.current_agent = "system"


def unregister_thread_callback():
    """Remove the callback for the current thread."""
    _thread_local.log_callback = None
    _thread_local._log_buf = ""


def set_current_agent(agent: str):
    """Update the agent label for the current thread's log lines."""
    _thread_local.current_agent = agent
