"""Retry utilities for handling transient Gemini API errors."""

import functools
import logging
import time
from typing import Any, Callable, Optional, TypeVar

from google.genai import errors

logger = logging.getLogger(__name__)

T = TypeVar("T")


def retry_with_backoff(
    max_retries: int = 4,
    initial_delay: float = 2.0,
    backoff_factor: float = 2.0,
    retryable_codes: tuple[int, ...] = (429, 500, 502, 503, 504),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to retry API calls on transient errors with exponential backoff."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            delay = initial_delay
            last_err: Optional[Exception] = None
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except errors.APIError as err:
                    last_err = err
                    code = getattr(err, "code", None)
                    if code is not None and code not in retryable_codes:
                        raise
                    if attempt == max_retries:
                        raise
                    print(
                        f"\n⚠️ Transient API error (attempt {attempt}/{max_retries}): {err}. Retrying in {delay:.1f}s...",
                        flush=True,
                    )
                    time.sleep(delay)
                    delay *= backoff_factor
                except Exception as err:
                    last_err = err
                    err_msg = str(err).lower()
                    if any(x in err_msg for x in ("503", "429", "timeout", "unavailable", "overloaded", "connection")):
                        if attempt == max_retries:
                            raise
                        print(
                            f"\n⚠️ Network/service error (attempt {attempt}/{max_retries}): {err}. Retrying in {delay:.1f}s...",
                            flush=True,
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        raise
            if last_err:
                raise last_err
            raise RuntimeError("Exceeded maximum retries")

        return wrapper

    return decorator
