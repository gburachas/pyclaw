"""Fallback chain for trying multiple LLM providers."""

from __future__ import annotations

import logging
import time
from typing import Any

from pytoclaw.models import (
    FallbackAttempt,
    FallbackCandidate,
    FailoverReason,
    LLMResponse,
    Message,
    ToolDefinition,
)
from pytoclaw.protocols import LLMProvider

logger = logging.getLogger(__name__)


class FallbackChain:
    """Tries multiple provider/model candidates in sequence."""

    def __init__(self, providers: dict[str, LLMProvider]):
        self._providers = providers
        self._cooldowns: dict[str, float] = {}
        self._cooldown_seconds = 60.0

    async def execute(
        self,
        candidates: list[FallbackCandidate],
        messages: list[Message],
        tools: list[ToolDefinition],
        options: dict[str, Any] | None = None,
    ) -> tuple[LLMResponse, list[FallbackAttempt]]:
        """Try candidates in order, returning first successful response."""
        attempts: list[FallbackAttempt] = []

        for candidate in candidates:
            provider = self._providers.get(candidate.provider)
            if provider is None:
                attempts.append(FallbackAttempt(
                    provider=candidate.provider,
                    model=candidate.model,
                    error=f"Provider '{candidate.provider}' not found",
                    reason=FailoverReason.UNKNOWN,
                    skipped=True,
                ))
                continue

            # Check cooldown
            key = f"{candidate.provider}:{candidate.model}"
            if key in self._cooldowns:
                if time.time() - self._cooldowns[key] < self._cooldown_seconds:
                    attempts.append(FallbackAttempt(
                        provider=candidate.provider,
                        model=candidate.model,
                        error="In cooldown",
                        reason=FailoverReason.RATE_LIMIT,
                        skipped=True,
                    ))
                    continue

            start = time.time()
            try:
                response = await provider.chat(messages, tools, candidate.model, options)
                duration_ms = (time.time() - start) * 1000
                attempts.append(FallbackAttempt(
                    provider=candidate.provider,
                    model=candidate.model,
                    duration_ms=duration_ms,
                ))
                return response, attempts
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                reason = _classify_error(e)
                self._cooldowns[key] = time.time()
                attempts.append(FallbackAttempt(
                    provider=candidate.provider,
                    model=candidate.model,
                    error=str(e),
                    reason=reason,
                    duration_ms=duration_ms,
                ))
                logger.warning(
                    "Provider %s/%s failed (%s): %s",
                    candidate.provider, candidate.model, reason, e,
                )

        raise RuntimeError(
            f"All {len(candidates)} provider candidates failed. "
            f"Attempts: {[a.model_dump() for a in attempts]}"
        )


def _classify_error(error: Exception) -> FailoverReason:
    """Classify an error into a failover reason."""
    msg = str(error).lower()
    if "401" in msg or "403" in msg or "auth" in msg:
        return FailoverReason.AUTH
    if "429" in msg or "rate" in msg:
        return FailoverReason.RATE_LIMIT
    if "402" in msg or "billing" in msg or "quota" in msg:
        return FailoverReason.BILLING
    if "timeout" in msg or "timed out" in msg:
        return FailoverReason.TIMEOUT
    if "overloaded" in msg or "529" in msg or "503" in msg:
        return FailoverReason.OVERLOADED
    return FailoverReason.UNKNOWN
