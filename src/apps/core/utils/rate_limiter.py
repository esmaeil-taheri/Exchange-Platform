"""
Sliding Window Rate Limiter — Redis Sorted Sets

Algorithm:
    Each request is added to a sorted set with a unique member
    (nanosecond timestamp) and the score equal to the request time.
    Entries older than the window are removed.
    Remaining members count = number of requests in the current window.

Advantages over Fixed Window:
    - No spike at the start of each minute
    - The most accurate rate limiting method
    - Fully atomic (Redis pipeline)

Redis DB: 2  (0=default, 1=otp, 2=ratelimit)
"""

import time
import logging
from typing import Tuple

from django_redis import get_redis_connection

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Sliding window rate limiter backed by Redis sorted sets.

    Usage:
        limiter = RateLimiter()
        allowed, meta = limiter.check('otp_send', '192.168.1.1', limit=5, window=600)
        if not allowed:
            raise RateLimitExceeded(retry_after=meta['retry_after'])
    """

    def __init__(self, cache_alias: str = 'ratelimit'):
        self._cache_alias = cache_alias

    @property
    def _redis(self):
        return get_redis_connection(self._cache_alias)

    def check(
        self,
        scope: str,
        identifier: str,
        limit: int,
        window: int,
    ) -> Tuple[bool, dict]:
        """
        Check if the request is within the rate limit.

        Args:
            scope:      Namespace for this rule (e.g. 'otp_send_ip')
            identifier: Unique identifier (e.g. IP address or phone number)
            limit:      Maximum allowed requests within the window
            window:     Time window in seconds

        Returns:
            (is_allowed, metadata)
            metadata keys:
                limit       — request limit
                remaining   — remaining requests
                retry_after — seconds until next allowed request (if blocked)
        """
        key = f"rl:{scope}:{identifier}"
        now_sec = time.time()
        now_ns = time.time_ns()
        window_start = now_sec - window

        try:
            pipe = self._redis.pipeline()
            # 1. Remove members outside the window
            pipe.zremrangebyscore(key, '-inf', window_start)
            # 2. Add current request (unique member = nanoseconds)
            pipe.zadd(key, {str(now_ns): now_sec})
            # 3. Count members within the window
            pipe.zcard(key)
            # 4. Set TTL on the key (slightly longer than the window)
            pipe.expire(key, window + 1)
            _, _, count, _ = pipe.execute()

        except Exception as e:
            # Redis unavailable → fail open (do not block the user)
            logger.error(f"[rate_limiter] Redis error — failing open | scope={scope} error={e}")
            return True, {'limit': limit, 'remaining': 1, 'retry_after': 0}

        is_allowed = count <= limit
        remaining = max(0, limit - count)

        retry_after = 0
        if not is_allowed:
            try:
                oldest = self._redis.zrange(key, 0, 0, withscores=True)
                if oldest:
                    oldest_ts = oldest[0][1]
                    retry_after = max(1, int(oldest_ts + window - now_sec) + 1)
                else:
                    retry_after = window
            except Exception:
                retry_after = window

        return is_allowed, {
            'limit': limit,
            'remaining': remaining,
            'retry_after': retry_after,
        }

    def reset(self, scope: str, identifier: str) -> None:
        """Clear a user's rate limit (e.g. after successful login)."""
        key = f"rl:{scope}:{identifier}"
        try:
            self._redis.delete(key)
        except Exception as e:
            logger.error(f"[rate_limiter] Failed to reset key | scope={scope} error={e}")


# ── Singleton importable everywhere ─────────────────────────────────────────
limiter = RateLimiter(cache_alias='ratelimit')
