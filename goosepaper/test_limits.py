"""Tests that provider `limit` values are honored end-to-end, even when
they exceed the method-level default of `get_stories`."""

from types import SimpleNamespace

import pytest

from .goosepaper import Goosepaper
from .storyprovider.storyprovider import LoremStoryProvider


# ---- LoremStoryProvider (covers the generic pattern) ----------------------


def test_lorem_respects_self_limit_above_method_default():
    stories = LoremStoryProvider(limit=10).get_stories()
    assert len(stories) == 10


def test_goosepaper_passes_through_configured_limits():
    g = Goosepaper([LoremStoryProvider(limit=10), LoremStoryProvider(limit=8)])
    assert len(g.get_stories()) == 18


def test_goosepaper_get_stories_limit_argument_caps_providers():
    g = Goosepaper([LoremStoryProvider(limit=10), LoremStoryProvider(limit=10)])
    assert len(g.get_stories(limit=3)) == 6


# ---- RSS / Mastodon / Reddit (mock feedparser) ----------------------------


class _Entry(dict):
    """Behaves like both feedparser's attribute-access and dict-access entries."""

    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError as e:
            raise AttributeError(item) from e


def _fake_feed(n_entries: int):
    entries = [
        _Entry(
            title=f"t{i}",
            summary=f"s{i}",
            link=f"https://example.com/{i}",
            author="author",
            updated_parsed=(2026, 1, 1, 0, 0, 0, 0, 0, 0),
            published_parsed=(2026, 1, 1, 0, 0, 0, 0, 0, 0),
        )
        for i in range(n_entries)
    ]
    return SimpleNamespace(entries=entries)


def test_rss_respects_self_limit_above_method_default(monkeypatch):
    from .storyprovider import rss

    monkeypatch.setattr(rss, "feedparser", SimpleNamespace(parse=lambda url: _fake_feed(50)))
    # Short-circuit the network fetch inside the loop: make requests return a
    # failed response so the provider takes the "headline only" branch.
    class _Resp:
        ok = False

    monkeypatch.setattr(rss, "requests", SimpleNamespace(get=lambda *a, **k: _Resp()))

    provider = rss.RSSFeedStoryProvider(rss_path="http://example.com/feed", limit=20)
    assert len(provider.get_stories()) == 20


def test_mastodon_respects_self_limit_above_method_default(monkeypatch):
    from .storyprovider import mastodon

    monkeypatch.setattr(
        mastodon, "feedparser", SimpleNamespace(parse=lambda url: _fake_feed(50))
    )
    provider = mastodon.MastodonStoryProvider(
        server="https://example.social", username="u", limit=20
    )
    assert len(provider.get_stories()) == 20


def test_reddit_respects_self_limit_above_method_default(monkeypatch):
    from .storyprovider import reddit

    monkeypatch.setattr(
        reddit, "feedparser", SimpleNamespace(parse=lambda url: _fake_feed(60))
    )
    provider = reddit.RedditHeadlineStoryProvider(subreddit="x", limit=50)
    assert len(provider.get_stories()) == 50
