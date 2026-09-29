"""Tips: every context gets tips, key tips exist for their template slugs, links point at real help pages."""

import re
from pathlib import Path

from aggrssive import help as helpmod
from aggrssive import tips

TEMPLATES = Path("aggrssive/templates")


def test_every_context_gets_specific_tips_first():
    for ctx in ("find", "sources", "bookmarks", "bundles", "lti", "admin"):
        got = tips.tips_for(f"/{ctx}/anything")
        assert got and ctx in got[0].where and got[0].where[0] == ctx, ctx
    assert tips.tips_for("/")  # home gets the general ones
    assert tips.context_for_path("/b/slug/feed.rss") == "bundles" and tips.context_for_path("/tags/x") == "find"


def test_links_point_at_real_help_pages():
    slugs = set(helpmod.pages())
    for t in tips.TIPS:
        assert not t.link or (t.link.startswith("/help/") and t.link.split("/")[2] in slugs), t.link


def test_key_tip_slugs_used_in_templates_exist():
    used = set()
    for f in TEMPLATES.glob("*.html"):
        used |= set(re.findall(r'key_tip\("([a-z-]+)"\)', f.read_text()))
    assert used and used <= set(tips.KEY_TIPS), used - set(tips.KEY_TIPS)
    assert tips.key_tip("nope") == ""
