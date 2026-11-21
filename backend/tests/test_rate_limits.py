"""Tests for the counts behind the daily caps and the abuse limits (spec 014)."""

import pytest

from subbed import config, rate_limits
from subbed.rate_limits import Limit, count_if_allowed, uncount


class FakeTime:
    def __init__(self, now: float) -> None:
        self.now = now

    def time(self) -> float:
        return self.now


def test_the_shipped_caps_are_the_ones_the_spec_names() -> None:
    assert (
        config.NEW_SONGS_PER_ACCOUNT_PER_DAY,
        config.NEW_SONGS_PER_GUEST_IP_PER_DAY,
        config.NEW_SONGS_PER_SITE_PER_DAY,
        config.SIGN_UPS_PER_IP_PER_DAY,
        config.FAILED_SIGN_INS_PER_USERNAME_PER_HOUR,
    ) == (20, 20, 300, 5, 10)


def test_a_reached_limit_counts_toward_none_of_the_limits() -> None:
    person = Limit("new_song_account", "1", 5, config.DAY_SECONDS)
    site = Limit("new_song_site", "site", 1, config.DAY_SECONDS)
    assert count_if_allowed(person, site)

    assert not count_if_allowed(person, site)

    # The person's count stayed at 1, so 4 more fit once the site has room.
    bigger_site = site._replace(most=100)
    assert all(count_if_allowed(person, bigger_site) for _ in range(4))
    assert not count_if_allowed(person, bigger_site)


def test_a_new_utc_day_starts_a_new_count(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = FakeTime(10 * config.DAY_SECONDS + 100)
    monkeypatch.setattr(rate_limits, "time", clock)
    limit = Limit("sign_up", "127.0.0.1", 1, config.DAY_SECONDS)
    assert count_if_allowed(limit)
    assert not count_if_allowed(limit)

    clock.now = 11 * config.DAY_SECONDS

    assert count_if_allowed(limit)


def test_a_full_hour_waits_until_the_next_hour(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = FakeTime(5 * config.HOUR_SECONDS)
    monkeypatch.setattr(rate_limits, "time", clock)
    limit = Limit("failed_sign_in", "mika", 2, config.HOUR_SECONDS)
    assert count_if_allowed(limit) and count_if_allowed(limit)
    assert not count_if_allowed(limit)

    clock.now += config.HOUR_SECONDS

    assert count_if_allowed(limit)


def test_uncount_gives_one_back() -> None:
    limit = Limit("failed_sign_in", "mika", 1, config.HOUR_SECONDS)
    assert count_if_allowed(limit)

    uncount(limit)

    assert count_if_allowed(limit)
