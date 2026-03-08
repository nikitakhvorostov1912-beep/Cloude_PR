"""Abstract base agent with retry, structured logging, and metrics."""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class AgentMetrics:
    """Lightweight metrics for a single agent invocation."""

    invocations: int = 0
    successes: int = 0
    failures: int = 0
    total_latency_ms: float = 0.0
    total_tokens: int = 0
    last_error: Optional[str] = None
    started_at: float = field(default_factory=time.monotonic)

    @property
    def avg_latency_ms(self) -> float:
        if self.invocations == 0:
            return 0.0
        return self.total_latency_ms / self.invocations

    @property
    def success_rate(self) -> float:
        if self.invocations == 0:
            return 0.0
        return self.successes / self.invocations


class BaseAgent(ABC):
    """Base class for all AI agents in the ecosystem.

    Provides:
    - Retry with exponential backoff
    - Structured logging with call_id binding
    - Metrics collection
    - Graceful error handling
    """

    def __init__(
        self,
        *,
        name: str,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 10.0,
    ) -> None:
        self.name = name
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._metrics = AgentMetrics()

    @property
    def metrics(self) -> AgentMetrics:
        return self._metrics

    async def execute_with_retry(
        self,
        call_id: str,
        **kwargs: Any,
    ) -> Any:
        """Execute the agent's main logic with retry on transient errors."""
        self._metrics.invocations += 1
        start = time.monotonic()
        last_exc: Optional[Exception] = None

        for attempt in range(1, self._max_retries + 1):
            try:
                result = await self._execute(call_id=call_id, **kwargs)
                elapsed = (time.monotonic() - start) * 1000
                self._metrics.successes += 1
                self._metrics.total_latency_ms += elapsed
                logger.info(
                    "agent=%s call_id=%s attempt=%d ok latency=%.0fms",
                    self.name,
                    call_id,
                    attempt,
                    elapsed,
                )
                return result
            except Exception as exc:
                last_exc = exc
                self._metrics.last_error = str(exc)
                logger.warning(
                    "agent=%s call_id=%s attempt=%d/%d error=%s",
                    self.name,
                    call_id,
                    attempt,
                    self._max_retries,
                    exc,
                )
                if attempt < self._max_retries and self._is_retryable(exc):
                    delay = min(self._base_delay * (2 ** (attempt - 1)), self._max_delay)
                    await asyncio.sleep(delay)
                else:
                    break

        elapsed = (time.monotonic() - start) * 1000
        self._metrics.failures += 1
        self._metrics.total_latency_ms += elapsed
        logger.error(
            "agent=%s call_id=%s exhausted_retries latency=%.0fms",
            self.name,
            call_id,
            elapsed,
        )
        raise last_exc  # type: ignore[misc]

    @abstractmethod
    async def _execute(self, *, call_id: str, **kwargs: Any) -> Any:
        """Override in subclasses with actual agent logic."""

    def _is_retryable(self, exc: Exception) -> bool:
        """Determine if an exception is transient and worth retrying.

        Override in subclasses for custom logic.
        """
        retryable_types = (
            ConnectionError,
            TimeoutError,
            asyncio.TimeoutError,
        )
        return isinstance(exc, retryable_types)
