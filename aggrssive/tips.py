"""Tips: short, rotating hints shown on each page, and fixed "key tips" beside the practices people get wrong.

All wording lives here so it stays in one place beside the help pages. A tip's `where` names the page contexts it
suits (the first path segment, or "any"); `link` points at the help page that says more. Key tips are looked up
by slug from templates with {{ key_tip('slug') }} and shown every time; rotating tips can be dismissed.
"""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Tip:
    text: str
    where: tuple[str, ...] = ("any",)
    link: str = ""  # "/help/page" for "more"


TIPS: tuple[Tip, ...] = (
    # Finding and searching
    Tip("Search <em>Find feeds</em> with a whole phrase, not a keyword: “students using generative AI to write essays” finds far more than “AI”.", ("find", "any"), "/help/tags-and-classification"),
    Tip("<em>Feeds writing about this</em> ranks sources by what they actually publish, not by their name or tags. It is the fastest way to find a feed you did not know existed.", ("find",), "/help/tags-and-classification"),
    Tip("A classification heading includes everything filed beneath it: pick <em>L Education</em> and you get LB, LC and the rest. <em>Make an aggRSSive from these</em> bundles the lot in one click.", ("find", "classification"), "/help/tags-and-classification"),
    Tip("Tags say what people call a feed; classification says where it belongs. Use both: a teaching-of-chemistry blog deserves an Education heading and a Chemistry one.", ("find", "sources", "classification"), "/help/tags-and-classification"),
    Tip("Tag clouds are alphabetical by default. Prefer the busiest tags first? Change it under your name → Account.", ("find", "tags"), "/help/roles"),
    # Adding sources
    Tip("Paste the page you would normally look at: a YouTube channel, a Mastodon or Bluesky account, a Zotero group or a Hypothesis user. aggRSSive knows where each platform hides its feed.", ("sources", "any"), "/help/sources"),
    Tip("A page with no feed can still be a source: when discovery finds nothing, <em>Watch the page instead</em> reports new links on it, or changes to its text.", ("sources", "any"), "/help/sources"),
    Tip("A Mastodon hashtag page (<code>https://instance/tags/opened</code>) works as a source: every public post with that tag, from that server.", ("sources",), "/help/sources"),
    Tip("Import an OPML file from your feed reader and its folders become tags. Importing the same file again is safe: nothing is duplicated.", ("sources", "find"), "/help/sources"),
    Tip("A feed that mixes what you want with what you don't? Put an <em>exclude</em> rule on the source itself and it applies everywhere that feed is used.", ("sources",), "/help/bundles"),
    Tip("Suggested tags are proposals: ✓ adds, ✎ lets you edit first, ✕ rejects for good. Nothing is applied until you click.", ("sources",), "/help/tags-and-classification"),
    # Bookmarks
    Tip("Drag <em>♥ aggRSSive this</em> from the Bookmarks page to your browser's bookmarks bar. One click on any article and it is described and ready to save.", ("bookmarks", "any"), "/help/bookmarks"),
    Tip("A bookmark list is a source like any other: put it in an aggRSSive next to feeds. Pin your hand-picked readings at the top and let the feeds fill in below.", ("bookmarks", "bundles"), "/help/bookmarks"),
    Tip("Your note on a bookmark travels with it: it shows on the aggRSSive's page, in embeds and in courses.", ("bookmarks",), "/help/bookmarks"),
    # Bundles and rules
    Tip("Exclude rules always win. If something you want keeps disappearing, look at the excludes first; <em>Preview: kept out</em> says which rule did it.", ("bundles",), "/help/bundles"),
    Tip("A <em>meaning</em> rule takes a description, not a keyword: “assessment and grading practices in higher education”. Set it to <em>loose</em> for a wide net, <em>strict</em> for close matches.", ("bundles", "any"), "/help/bundles"),
    Tip("New items show as <em>pending</em> for a few minutes until the local model has read them. An include rule keeps them out until then; an exclude rule lets them through.", ("bundles",), "/help/bundles"),
    Tip("<em>Feeds like these</em> follows your rules: tighten the rules and the suggested feeds tighten with them.", ("bundles",), "/help/bundles"),
    Tip("Pinning an item forces it in regardless of rules and keeps it at the top. Hiding removes it even if rules would include it.", ("bundles",), "/help/bundles"),
    Tip("Choose <em>all</em> match mode when include rules should combine (“about assessment <em>and</em> mentions rubrics”); <em>any</em> when they are alternatives.", ("bundles",), "/help/bundles"),
    Tip("Like someone's aggRSSive? <em>Copy to my aggRSSives</em> gives you a private copy with the same sources and rules to adapt.", ("bundles", "any"), "/help/bundles"),
    Tip("Prefer email? <em>By email</em> on an aggRSSive's page sends you its new items daily or weekly, and nothing at all when there is nothing new.", ("bundles",), "/help/publishing"),
    Tip("Every aggRSSive is itself a feed. Add one aggRSSive as a source of another to build lists of lists.", ("bundles",), "/help/publishing"),
    Tip("An age window (“items newer than 30 days”) keeps a course page current without anyone touching it.", ("bundles",), "/help/bundles"),
    Tip("Under each item, <em>related posts</em> shows the closest posts from the whole collection. It is a quick way to spot a feed worth adding.", ("bundles", "any"), "/help/publishing"),
    # Publishing and LTI
    Tip("The embed's script tag takes attributes: <code>data-n=\"8\"</code>, <code>data-desc=\"0\"</code>, <code>data-theme=\"dark\"</code>. Sites that strip scripts can use the iframe version.", ("bundles",), "/help/publishing"),
    Tip("In Moodle, add an aggRSSive with <em>External tool → Select content</em>. The course shows the live list; edit the aggRSSive and the course follows.", ("bundles", "any"), "/help/lti-instructors"),
    Tip("A platform without a content picker can still launch an aggRSSive from a plain URL: <code>…/lti/launch?bundle=CODE</code>.", ("lti",), "/help/lti-instructors"),
    Tip("Moodle on the same cloud as aggRSSive? Paste the public key into the tool settings (<em>Public key type: RSA key</em>) instead of relying on the keyset URL.", ("lti",), "/help/lti-admin"),
    Tip("Platform quirks are settings, not code: under each registered platform, <em>Settings for this platform</em> controls related posts, link targets, frame height and picker defaults.", ("lti", "admin"), "/help/lti-admin"),
    # Admin and GenAI
    Tip("Once your colleagues have accounts, close sign-ups on the Admin page. New people can still be added by an admin.", ("admin",), "/help/roles"),
    Tip("Starter collections are verified, tagged and classified, and deliberately include Indigenous, gender-equity and Global South sources. Import one, then prune.", ("admin", "find"), "/help/sources"),
    Tip("GenAI features only ever propose; a person accepts or rejects. A plain-language rule judges each item once and remembers the verdict, so it costs a fraction of a cent per new item.", ("bundles", "admin", "sources"), "/help/genai"),
    Tip("Tick <em>Suggest tags and classification (GenAI)</em> when adding a feed and the proposals will be waiting on the source's page after the first fetch.", ("sources",), "/help/genai"),
    # General
    Tip("The Help pages change with the software: <em>What's new</em> lists every feature as it lands.", ("any",), "/help/changelog"),
    Tip("Tired of tips? Turn them off under your name → Account, or hide them on a page with ×.", ("any",), "/help/index"),
)

KEY_TIPS: dict[str, str] = {
    "rules": "<strong>How rules combine:</strong> exclude rules always win; with no include rules everything gets through; with include rules an item must match <em>any</em> (or <em>all</em>, under Settings). Meaning rules take a description and a strictness; plain-language rules are judged once by the GenAI and remembered.",
    "source-rules": "<strong>Rules here apply everywhere this source is used.</strong> Good for “never the comments feed's entries”; for “only in this list”, put the rule on the aggRSSive instead.",
    "pending": "<strong>Pending</strong> means a meaning or plain-language rule has not read the item yet (a few minutes). Include rules hold pending items out; exclude rules let them through. Pin an item to force it in now.",
    "strictness": "<strong>Strictness</strong> is how close an item's meaning must be to your description: <em>loose</em> catches related items too, <em>strict</em> wants a close match, <em>normal</em> suits most lists. Check <em>Preview: kept out</em> and adjust.",
    "classification": "<strong>File at the most specific heading that fits</strong> (LB says more than L), and file under both frameworks when both apply. A heading is a controlled vocabulary: you can't invent one, so two people filing similar feeds land in the same place.",
    "bookmarklet": "<strong>To install the bookmarklet, drag the button to your bookmarks bar</strong> (clicking it here does nothing). It opens aggRSSive in a small window with the page already described. If a site can't be read, the form is blank: fill it in yourself.",
    "platforms": "<strong>Platform pages work as-is:</strong> paste <code>youtube.com/@name</code>, <code>bsky.app/profile/name</code>, <code>instance/@name</code>, <code>zotero.org/groups/…</code> or <code>hypothes.is/users/name</code>. Only public content is ever read; private Zotero groups can't be.",
    "same-cloud": "<strong>Same cloud as your LMS?</strong> Registration or launches failing with “connection refused” or “signature verification failed” usually means the two sites can't reach each other by name. Set <code>DNS_OVERRIDES</code> on aggRSSive and paste the public key below into the platform's tool settings.",
    "platform-settings": "<strong>Change behaviour per platform here, never by editing code.</strong> The defaults match Moodle. Turn off <em>JWT in return URL</em> only if a platform rejects long URLs; turn off <em>new tab</em> if a platform prefers navigation inside its frame.",
    "picker": "<strong>What you pick stays live:</strong> the course shows the aggRSSive as it is now and as it changes. To show something else later, edit the activity and pick again; to change what's in it, edit the aggRSSive.",
    "embed": "<strong>Embed options go on the script tag:</strong> <code>data-n</code> items, <code>data-desc</code> (<code>0</code>, <code>full</code>), <code>data-img</code>, <code>data-src</code>, <code>data-date</code>, <code>data-theme</code>, <code>data-target</code>. Sites that strip scripts (many LMS editors) take the iframe instead.",
    "opml": "<strong>Folders become tags</strong> when the box is ticked; the file's <code>category</code> attributes become classification headings. Re-importing is safe: existing feeds are skipped, new tags are added.",
    "watch": "<strong>No feed? Watch the page.</strong> <em>New links</em> treats the page as a list and reports each article-like link once, when it first appears. <em>Changes</em> reports what was added or removed in the page's own text. Both are checked on the normal schedule; the first check only takes a snapshot.",
    "heart-cart": "<strong>Tick sources anywhere</strong> (Find feeds, a tag, a heading, a source page, Bookmarks) and they collect in the ♥ Heart-Cart at the bottom right. Name the cart to create an aggRSSive, or add it to one you already have.",
}

CONTEXTS = sorted({w for t in TIPS for w in t.where})


def context_for_path(path: str) -> str:
    """The tip context for a URL path: its first segment, with a few aliases."""
    seg = path.strip("/").split("/")[0] if path.strip("/") else "home"
    return {"b": "bundles", "embed": "bundles", "tags": "find", "classification": "find", "items": "bundles"}.get(seg, seg)


def tips_for(path: str) -> list[Tip]:
    """Tips for this page's context first, then general ones; the page rotates through them."""
    ctx = context_for_path(path)
    specific = [t for t in TIPS if ctx in t.where and t.where[0] == ctx]
    general = [t for t in TIPS if t not in specific and ("any" in t.where or ctx in t.where)]
    random.shuffle(specific)
    random.shuffle(general)
    return specific + general


def key_tip(slug: str) -> str:
    return KEY_TIPS.get(slug, "")
