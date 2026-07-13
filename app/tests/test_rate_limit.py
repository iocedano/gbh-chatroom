from infra.rate_limit import LimitsRateLimiter


def test_limits_rate_limiter_blocks_after_max_events():
    limiter = LimitsRateLimiter(max_events=2, window_seconds=60)

    assert limiter.check("user:1").allowed is True
    assert limiter.check("user:1").allowed is True

    result = limiter.check("user:1")

    assert result.allowed is False
    assert result.retry_after_seconds >= 1


def test_limits_rate_limiter_reset_clears_events():
    limiter = LimitsRateLimiter(max_events=1, window_seconds=60)

    assert limiter.check("user:1").allowed is True
    assert limiter.check("user:1").allowed is False

    limiter.reset()

    assert limiter.check("user:1").allowed is True
