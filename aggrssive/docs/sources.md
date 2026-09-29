---
title: Adding feeds
order: 2
---

# Adding feeds

A **source** is a feed: RSS, Atom or JSON Feed. Sources are shared — once anyone adds one, everyone can tag it, classify it and put it in a bundle.

## Add one feed

Click **+ Add feed** and paste any address. You don't need to know the feed URL: aggRSSive looks at the page and finds it.

Works for:

- blogs and news sites (WordPress, Ghost, Substack, Medium…)
- journals and repositories (arXiv, PubMed, many library discovery systems, OER Commons)
- anything that already is a feed URL
- the platforms below, by pasting the page you'd normally look at

## Platforms that hide their feeds

Paste the ordinary page address; aggRSSive knows where each platform keeps its feed. Items arrive as normal posts, so they can be tagged, filtered, bundled, embedded and placed in a course like anything else.

| Paste | What you get |
|---|---|
| A **YouTube** channel (`youtube.com/@name`, `/channel/UC…`) or a playlist | New videos, with thumbnails |
| A **Mastodon** account (`https://instance/@name`) or hashtag page (`https://instance/tags/topic`) | Public posts. Works on any Mastodon-compatible server |
| A **Bluesky** profile (`bsky.app/profile/name`) | Public posts |
| A public **Zotero** group (`zotero.org/groups/…`) or a person's public library (`zotero.org/username`) | Newest items with a formatted citation. Private groups and libraries can't be read |
| A **Hypothesis** user (`hypothes.is/users/name`), group, or tag search (`hypothes.is/search?q=tag:topic`) | Public annotations, with the quoted passage and the note |

The source page shows a small badge naming the platform. Because these are public feeds, only public content ever appears; nothing needs an account or a key.

If several feeds are found (a site's posts and its comments, say), pick the one you want. Give it tags as you add it; existing tags are suggested below the form so the vocabulary stays consistent.

If **✨ Suggest tags and classification (GenAI)** is ticked, aggRSSive proposes tags and classification headings once the feed has been fetched. Nothing is applied until you accept each proposal on the source's page. The option only appears when your site has GenAI enabled — see [GenAI features](genai).

## Pages without a feed

Some pages worth following have no feed at all: a department's news page, a journal's "latest articles" list, a policy that changes quietly. When **+ Add feed** finds no feed, it offers to **watch the page instead**, in one of two ways:

- **New links** treats the page as a list. Each article-like link (a real title, not a menu entry) becomes an item the first time it is seen; menus, footers and sidebars are ignored. Right for news pages, publication lists and event listings.
- **Changes** keeps the page's own text and, whenever it changes, adds one item saying what was added and what was removed. Right for policies, syllabi, calls for papers and anything else where the page *is* the content.

Watched pages are checked on the same schedule as feeds, show a badge on their source page, and behave like any source afterwards. The first check only takes a snapshot; items start with the next change. Pages that need a login, or that build their content with scripts after loading, can't be watched.

## Import many at once (OPML)

Feed readers export subscriptions as an OPML file. On *Find feeds*, use **Import OPML** in the sidebar. Folders in the file become tags if you leave *Turn folders into tags* ticked. Importing the same file again is safe: feeds you already have are skipped, new tags are added.

Starter collections curated for education are available to site admins under *Admin → Starter collections*. The shipped collection spans open education and OER, teaching and learning, ed-tech analysis, higher-education news, journals, libraries and scholarly communication, accessibility and the open web, podcasts, and — on purpose — Indigenous knowledge and media, gender equity, and intercultural and Global South perspectives. A second collection, **GenAI in higher education**, gathers the research, practitioner, policy and Canadian sources tracked by a companion research project: its tags carry each source's stance (critical, adoption-positive, institutional…) and credibility tier (peer-reviewed, preprint, editorial…), so a bundle can be built for one perspective or one rigour level. Every feed was alive when the collections were built; they are starting points, and pruning is expected. They carry tags and classification headings with them (in the OPML file's standard `category` attribute), so imported feeds arrive already filed.

## What happens after adding

The feed is fetched within a few seconds, then polled on a schedule (every 30 minutes by default). Feeds that fail repeatedly are polled less often, and marked with an *error* badge you can hover for the reason. Use **Fetch now** on the source's page to force a refresh.

## The source page

Each source has a page showing its recent items and, for signed-in users:

- **Tags** — add, remove, and review suggested tags.
- **Classification** — file the source under Library of Congress and ISCED-F headings; see [Tags and classification](tags-and-classification).
- **Rules for this source** — filters that apply wherever the source is used. Handy for a feed that mixes what you want with what you don't.
- **Details** — title, site link, description, and whether the feed is actively polled.
- **Delete** — available to the person who added the source and to admins. Bundles that used it lose it.
