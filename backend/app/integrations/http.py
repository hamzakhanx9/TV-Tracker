import logging
import time
from collections.abc import Callable
from copy import deepcopy
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from hashlib import sha256
from threading import Lock
from typing import Any

import httpx

from app.integrations.errors import ProviderError

logger = logging.getLogger(__name__)
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
CACHE_TTL_SECONDS = 300
MAX_CACHE_ENTRIES = 512
_cache: dict[str, tuple[float, Any]] = {}
_cache_lock = Lock()


def get_json(
    provider: str,
    url: str,
    *,
    params: dict[str, str | int] | None = None,
    headers: dict[str, str] | None = None,
    transport: httpx.BaseTransport | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> Any:
    key_material = repr(
        (provider, url, sorted((params or {}).items()), sorted((headers or {}).items()))
    )
    cache_key = sha256(key_material.encode()).hexdigest()
    now = time.monotonic()
    with _cache_lock:
        cached = _cache.get(cache_key)
        if cached and cached[0] > now:
            return deepcopy(cached[1])
        _cache.pop(cache_key, None)

    for attempt in range(3):
        try:
            with httpx.Client(
                timeout=httpx.Timeout(8.0, connect=3.0),
                transport=transport,
                follow_redirects=False,
            ) as client:
                response = client.get(url, params=params, headers=headers)
        except httpx.TimeoutException as exc:
            if attempt < 2:
                sleep(0.25 * (2**attempt))
                continue
            logger.warning("%s request timed out: %s", provider, url)
            raise ProviderError(
                provider, f"{provider} request timed out", unavailable=True
            ) from exc
        except httpx.RequestError as exc:
            logger.warning("%s request failed (%s)", provider, type(exc).__name__)
            raise ProviderError(provider, f"{provider} request failed", unavailable=True) from exc

        if response.status_code in RETRYABLE_STATUS_CODES and attempt < 2:
            sleep(_retry_delay(response, attempt))
            continue
        if response.status_code == 404:
            raise ProviderError(provider, "The requested title was not found", not_found=True)
        if response.is_error:
            logger.warning("%s returned HTTP %s", provider, response.status_code)
            raise ProviderError(
                provider,
                f"{provider} is temporarily unavailable",
                unavailable=response.status_code >= 500 or response.status_code == 429,
            )
        try:
            payload = response.json()
        except ValueError as exc:
            logger.warning("%s returned an invalid JSON response", provider)
            raise ProviderError(provider, f"{provider} returned an invalid response") from exc
        with _cache_lock:
            if len(_cache) >= MAX_CACHE_ENTRIES:
                _cache.pop(next(iter(_cache)))
            _cache[cache_key] = (time.monotonic() + CACHE_TTL_SECONDS, deepcopy(payload))
        return payload

    raise ProviderError(provider, f"{provider} request failed", unavailable=True)


def _retry_delay(response: httpx.Response, attempt: int) -> float:
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return min(10.0, max(0.0, float(retry_after)))
        except ValueError:
            try:
                retry_time = parsedate_to_datetime(retry_after)
                if retry_time.tzinfo is None:
                    retry_time = retry_time.replace(tzinfo=UTC)
                return min(10.0, max(0.0, (retry_time - datetime.now(UTC)).total_seconds()))
            except (TypeError, ValueError, OverflowError):
                pass
    return 0.25 * (2**attempt)
