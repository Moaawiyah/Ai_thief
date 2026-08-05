"""ApiGatekeeper: the single doorway for ALL external calls.

Every LLM / email / network call goes through execute(): rate limiting (config),
FIFO queuing on overflow, retry on transient provider errors, and call logging.
"""

import logging
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from thief_agent.exceptions import ProviderError, RateLimitError
from thief_agent.shared.config import ConfigManager
from thief_agent.shared.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

__all__ = ["ApiGatekeeper"]


class ApiGatekeeper:
    """Centralized API call manager with rate limiting and queuing."""

    def __init__(self, config: ConfigManager, service: str):
        self._service = service
        limits = config.service_limits(service)
        self._max_retries = limits.get("max_retries", 1)
        self._retry_after = limits.get("retry_after_seconds", 0)
        self._daily_quota = limits.get("daily_quota", 500)
        self._circuit_threshold = limits.get("circuit_breaker_failures", 5)
        self._circuit_cooldown = limits.get("circuit_breaker_cooldown_seconds", 60)
        self._limiter = RateLimiter(limits, config.rate_limits["queue"])
        self._concurrency = threading.BoundedSemaphore(limits.get("concurrent_max", 1))
        self._calls_total = 0
        self._failures_total = 0
        self._day = datetime.now(UTC).date()
        self._calls_today = 0
        self._consecutive_failures = 0
        self._circuit_opened_at = 0.0

    def execute(self, api_call: Callable, *args: Any, **kwargs: Any) -> Any:
        """Run an external call under rate control with transient-error retry."""
        last_error: ProviderError | None = None
        for attempt in range(1, self._max_retries + 1):
            self._check_guards()
            self._limiter.acquire()
            self._calls_total += 1
            self._calls_today += 1
            try:
                with self._concurrency:
                    result = api_call(*args, **kwargs)
                self._consecutive_failures = 0
                logger.debug("gatekeeper[%s] call ok (attempt %d)", self._service, attempt)
                return result
            except ProviderError as exc:
                self._failures_total += 1
                self._consecutive_failures += 1
                last_error = exc
                logger.warning(
                    "gatekeeper[%s] attempt %d/%d failed: %s",
                    self._service,
                    attempt,
                    self._max_retries,
                    exc,
                )
                if self._consecutive_failures >= self._circuit_threshold:
                    self._circuit_opened_at = time.monotonic()
                if attempt < self._max_retries and self._retry_after:
                    time.sleep(self._retry_after)
        assert last_error is not None
        raise last_error

    def _check_guards(self) -> None:
        """Enforce the daily quota and circuit-breaker cooldown."""
        today = datetime.now(UTC).date()
        if today != self._day:
            self._day, self._calls_today = today, 0
        if self._calls_today >= self._daily_quota:
            raise RateLimitError(f"daily quota exhausted for {self._service}")
        if self._circuit_opened_at:
            elapsed = time.monotonic() - self._circuit_opened_at
            if elapsed < self._circuit_cooldown:
                raise RateLimitError(f"circuit open for {self._service}")
            self._circuit_opened_at = 0.0
            self._consecutive_failures = 0

    def get_queue_status(self) -> dict:
        """Current queue depth and processing stats."""
        return {
            "service": self._service,
            "queue_depth": self._limiter.queue_depth,
            "calls_total": self._calls_total,
            "failures_total": self._failures_total,
            "calls_today": self._calls_today,
            "circuit_open": bool(self._circuit_opened_at),
        }
