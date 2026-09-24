"""Platform adapters: page URLs become the feed the platform serves. No network: page fetches are faked."""

from aggrssive.feeds import adapters
from aggrssive.feeds.adapters import adapt, bluesky, hypothesis, kind_for_feed_url, mastodon, youtube, zotero

YT_PAGE = '<html><head><title>Veritasium - YouTube</title><meta itemprop="identifier" content="UCHnyfMqiRRG1u-2MsSQLbXA"></head></html>'
ZOTERO_USER_PAGE = '<html><head><title>Zotero | People > Dan Stillman</title></head><script>var x={"userID":6}</script></html>'
ZOTERO_GROUP_PAGE = '<html><head><title>Zotero | Groups > Wordpress Sync Test Data</title></head><script>{"id":359247}</script></html>'


def test_youtube_handle_channel_and_playlist():
    a = youtube("https://www.youtube.com/@veritasium", fetch=lambda u: YT_PAGE)
    assert a.url == "https://www.youtube.com/feeds/videos.xml?channel_id=UCHnyfMqiRRG1u-2MsSQLbXA" and a.title == "Veritasium" and a.kind == "youtube"
    assert youtube("https://youtube.com/channel/UCHnyfMqiRRG1u-2MsSQLbXA").url.endswith("channel_id=UCHnyfMqiRRG1u-2MsSQLbXA")
    assert youtube("https://www.youtube.com/playlist?list=PL123abc").url.endswith("playlist_id=PL123abc")
    assert youtube("https://www.youtube.com/feeds/videos.xml?channel_id=UCx") is None  # already a feed
    assert youtube("https://example.com/@name") is None


def test_mastodon_account_and_tag():
    assert mastodon("https://mastodon.social/@Gargron").url == "https://mastodon.social/@Gargron.rss"
    assert mastodon("https://scholar.social/users/someone").url == "https://scholar.social/@someone.rss"
    a = mastodon("https://mastodon.social/tags/OpenEd")
    assert a.url == "https://mastodon.social/tags/OpenEd.rss" and a.title.startswith("#OpenEd")
    assert mastodon("https://mastodon.social/@Gargron.rss") is None


def test_bluesky_profile():
    assert bluesky("https://bsky.app/profile/bsky.app").url == "https://bsky.app/profile/bsky.app/rss"
    assert bluesky("https://bsky.app/profile/did:plc:abc/rss").url == "https://bsky.app/profile/did:plc:abc/rss"
    assert bluesky("https://example.com/profile/x") is None


def test_zotero_group_user_and_named_pages():
    assert zotero("https://www.zotero.org/groups/359247/wordpress_sync_test_data").url.startswith("https://api.zotero.org/groups/359247/items/top?format=atom")
    assert zotero("https://www.zotero.org/users/6/items").url.startswith("https://api.zotero.org/users/6/items/top?")
    a = zotero("https://www.zotero.org/dstillman", fetch=lambda u: ZOTERO_USER_PAGE)
    assert a.url.startswith("https://api.zotero.org/users/6/items/top?") and a.title == "Dan Stillman"
    a = zotero("https://www.zotero.org/groups/wordpress_sync_test_data", fetch=lambda u: ZOTERO_GROUP_PAGE)
    assert "groups/359247/" in a.url and a.title == "Wordpress Sync Test Data"
    assert zotero("https://api.zotero.org/groups/1/items?format=atom") is None


def test_hypothesis_user_group_and_tag_search():
    assert hypothesis("https://hypothes.is/users/jeremydean").url == "https://hypothes.is/stream.atom?user=jeremydean"
    assert hypothesis("https://hypothes.is/groups/abc123/my-group").url == "https://hypothes.is/stream.atom?group=abc123"
    assert hypothesis("https://hypothes.is/search?q=tag%3Aopened").url == "https://hypothes.is/stream.atom?tags=opened"
    assert hypothesis("https://hypothes.is/stream.atom?user=x") is None


def test_adapt_picks_first_match_and_never_raises(monkeypatch):
    monkeypatch.setattr(adapters, "ADAPTERS", (lambda u: 1 / 0, bluesky))
    assert adapt("https://bsky.app/profile/x").kind == "bluesky"
    assert adapt("https://example.com/blog") is None


def test_kind_for_feed_url():
    assert kind_for_feed_url("https://www.youtube.com/feeds/videos.xml?channel_id=UCx") == "youtube"
    assert kind_for_feed_url("https://mastodon.social/@Gargron.rss") == "mastodon"
    assert kind_for_feed_url("https://bsky.app/profile/x/rss") == "bluesky"
    assert kind_for_feed_url("https://api.zotero.org/groups/1/items/top?format=atom") == "zotero"
    assert kind_for_feed_url("https://hypothes.is/stream.atom?user=x") == "hypothesis"
    assert kind_for_feed_url("https://example.com/feed/") == "feed"
