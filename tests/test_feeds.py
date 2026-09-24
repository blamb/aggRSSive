from aggrssive.feeds.discover import looks_like_feed
from aggrssive.feeds.fetch import parse_body, sanitize, to_text
from aggrssive.feeds.opml import OpmlEntry, parse_opml, render_opml

RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>Test Blog</title><link>https://t.example</link>
<item><title>Hello &amp; welcome</title><link>https://t.example/1</link><guid>1</guid><pubDate>Mon, 01 Sep 2025 10:00:00 GMT</pubDate>
<description>&lt;p&gt;Hi &lt;script&gt;alert(1)&lt;/script&gt;&lt;img src="https://t.example/a.png"&gt;&lt;/p&gt;</description><category>news</category></item>
</channel></rss>"""

JSONFEED = b'{"version":"https://jsonfeed.org/version/1.1","title":"JF","items":[{"id":"a","url":"https://j.example/a","title":"A","content_html":"<b>bold</b>","date_published":"2025-09-01T10:00:00Z","tags":["x"]}]}'

OPML = b"""<opml version="2.0"><head><title>subs</title></head><body>
<outline text="Ed Tech"><outline type="rss" text="Blog" xmlUrl="https://b.example/feed" htmlUrl="https://b.example"/></outline>
<outline type="rss" text="Loose" xmlUrl="https://l.example/rss"/>
</body></opml>"""


def test_rss_parses_and_sanitizes():
    pf = parse_body(RSS, "application/rss+xml")
    assert pf.title == "Test Blog"
    e = pf.entries[0]
    assert e.title == "Hello & welcome"
    assert "<script" not in e.summary
    assert "<img" in e.summary
    assert e.image_url == "https://t.example/a.png"
    assert e.categories == ["news"]
    assert e.published_at.year == 2025


def test_jsonfeed_parses():
    pf = parse_body(JSONFEED, "application/feed+json")
    assert pf.title == "JF"
    assert pf.entries[0].content == "<b>bold</b>"
    assert pf.entries[0].categories == ["x"]


def test_looks_like_feed():
    assert looks_like_feed(RSS, "text/xml")[0]
    assert looks_like_feed(JSONFEED, "application/json")[0]
    assert not looks_like_feed(b"<html><body>hi</body></html>", "text/html")[0]


def test_sanitize_strips_dangerous_markup():
    out = sanitize('<a href="javascript:alert(1)" onclick="x()">x</a><iframe src="a"></iframe>')
    assert "javascript:" not in out and "onclick" not in out and "<iframe" not in out
    assert out.startswith("<a") and out.endswith(">x</a>")
    assert to_text("<p>Hello   <b>world</b></p>") == "Hello world"


def test_opml_by_folder_roundtrip_keeps_all_tags():
    entries = [OpmlEntry(feed_url="https://a.example/feed", title="A", folders=["edtech", "open"]), OpmlEntry(feed_url="https://b.example/feed", title="B")]
    xml = render_opml("out", entries, by_folder=True)
    assert xml.count("https://a.example/feed") == 2  # listed under each tag
    back = {e.feed_url: e for e in parse_opml(xml.encode())}
    assert len(back) == 2
    assert back["https://a.example/feed"].folders == ["edtech", "open"]
    assert back["https://b.example/feed"].folders == []


def test_opml_roundtrip():
    entries = parse_opml(OPML)
    assert [e.feed_url for e in entries] == ["https://b.example/feed", "https://l.example/rss"]
    assert entries[0].folders == ["Ed Tech"]
    xml = render_opml("out", [OpmlEntry(feed_url="https://x.example/f", title='A "quoted" & odd')])
    assert 'xmlUrl="https://x.example/f"' in xml
    assert "&quot;quoted&quot; &amp; odd" in xml
    assert parse_opml(xml.encode())[0].title == 'A "quoted" & odd'


def test_headline_for_untitled_posts():
    from aggrssive.feeds.fetch import headline

    assert headline("Short post") == "Short post"
    long = "I've just added a reviews plugin to the site. It works on every page and " + "x" * 80
    assert headline(long) == "I've just added a reviews plugin to the site."
    assert headline("word " * 40).endswith("…") and len(headline("word " * 40)) <= 101
