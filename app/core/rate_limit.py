import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable

from fastapi import Request

from app.core.errors import AppError


@dataclass
class RateLimitConfig:
    times: int
    window_seconds: float
    key_prefix: str = "default"


class RateLimiter:
    def __init__(self):
        self._buckets: dict[str, deque[float]] = {}
        self._lock = threading.Lock()
        self._configs: dict[str, RateLimitConfig] = {}

    def configure(self, name: str, config: RateLimitConfig) -> None:
        self._configs[name] = config

    def check(self, key: str, config_name: str = "default") -> None:
        config = self._configs.get(config_name)
        if config is None:
            raise ValueError(f"Rate limit config '{config_name}' not found")

        full_key = f"{config.key_prefix}:{key}"
        now = time.monotonic()

        with self._lock:
            bucket = self._buckets.setdefault(full_key, deque())
            while bucket and bucket[0] <= now - config.window_seconds:
                bucket.popleft()
            if len(bucket) >= config.times:
                raise AppError(429, "Too many requests. Please wait a moment and try again.")
            bucket.append(now)

    def reset(self, key: str, config_name: str = "default") -> None:
        config = self._configs.get(config_name)
        if config is None:
            return
        full_key = f"{config.key_prefix}:{key}"
        with self._lock:
            self._buckets.pop(full_key, None)


_rate_limiter = RateLimiter()

# Configure default rate limits
_rate_limiter.configure(
    "auth",
    RateLimitConfig(
        times=10,
        window_seconds=60,
        key_prefix="auth"
    )
)
_rate_limiter.configure("security", RateLimitConfig(times=20, window_seconds=60, key_prefix="security"))
_rate_limiter.configure("api", RateLimitConfig(times=100, window_seconds=60, key_prefix="api"))
_rate_limiter.configure("strict", RateLimitConfig(times=3, window_seconds=300, key_prefix="strict"))


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "anonymous"


def rate_limit(config_name: str = "default", use_user: bool = False) -> Callable:
    def dependency(request: Request) -> None:
        key = f"ip:{get_client_ip(request)}"
        _rate_limiter.check(key, config_name)

    return dependency

def get_rate_limiter() -> RateLimiter:
    return _rate_limiter