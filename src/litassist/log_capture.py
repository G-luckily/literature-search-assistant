from __future__ import annotations

import logging
from collections import deque
from typing import Any


class MemoryLogHandler(logging.Handler):
    """Captures log records in memory for the frontend log viewer."""

    def __init__(self, capacity: int = 500) -> None:
        super().__init__()
        self.records: deque[dict[str, Any]] = deque(maxlen=capacity)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            formatter = self.formatter
            if formatter:
                time_str = formatter.formatTime(record, "%H:%M:%S")
            else:
                time_str = record.asctime or ""
            self.records.append({
                "time": time_str,
                "level": record.levelname,
                "name": record.name,
                "message": record.getMessage(),
            })
        except Exception:
            self.handleError(record)


_LOG_HANDLER: MemoryLogHandler | None = None


def install_log_capture(capacity: int = 500) -> MemoryLogHandler:
    global _LOG_HANDLER
    if _LOG_HANDLER is None:
        _LOG_HANDLER = MemoryLogHandler(capacity)
        _LOG_HANDLER.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        logging.getLogger().addHandler(_LOG_HANDLER)
    return _LOG_HANDLER


def get_recent_logs(count: int = 200) -> list[dict[str, Any]]:
    if _LOG_HANDLER is None:
        return []
    records = list(_LOG_HANDLER.records)
    return records[-count:]
