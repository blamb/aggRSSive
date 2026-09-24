# aggRSSive

Collect feeds. Tag them together. Filter them down. Bundle them into an *aggRSSive* and republish it anywhere: as embed code for any web page, as a feed of its own, or (soon) as an LTI resource inside Moodle and other learning platforms.

A second edition of a tool first built at UBC in 2005 with Magpie RSS, Feed2JS and Freetag. Same idea, twenty years of better parts.

## What it does today (Phase 1)

- **Sources**: paste any URL and aggRSSive finds the feed (RSS, Atom, JSON Feed). Import an OPML file to bring in a whole reader's worth. Polls on a schedule with conditional requests; dead feeds back off automatically.
- **Tags**: a shared folksonomy. Anyone can tag any source; OPML folders become tags.
- **Heart-Cart**: tick sources anywhere in the site, then turn the cart into a new aggRSSive or add it to one you have.
- **Rules**: include/exclude by keyword, phrase or regex on title, text, author, URL or category. Rules on a source apply everywhere; rules on a bundle apply to that bundle. Exclude always wins. Dedupe and a max-age window are built in.
- **Curation**: pin, hide and annotate individual items in a bundle. Pinning overrides the rules.
- **Outputs** for every public bundle: a `<script>` embed (with iframe fallback), RSS, Atom, JSON Feed, a JSON API, and OPML of the sources.
- **Accounts**: local email/password; GitHub and Google sign-in when configured. The first account becomes admin.

## Run it locally

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
cp .env.example .env        # then edit SECRET_KEY at least
.venv/bin/uvicorn aggrssive.main:app --reload
```

Open http://localhost:8000 and create the first account.

## Run it with Docker

```bash
cp .env.example .env        # set SECRET_KEY and BASE_URL
docker compose up -d --build
```

The database lives in the `aggrssive-data` volume at `/data/aggrssive.db`. Back it up by copying that one file.

## Tests

```bash
.venv/bin/pytest
```

## Roadmap

1. ~~Sources, tags, bundles, rules, embed and feed outputs~~ (this release)
2. LTI 1.3 Advantage: Deep Linking picker and live resource inside Moodle; deploy to Reclaim Cloud
3. Local embeddings for semantic filtering; optional Claude-backed plain-language rules and tag suggestions
4. Manual bookmarks, platform adapters (YouTube, Mastodon, Bluesky, arXiv, Zotero, Hypothesis...), bundles as sources, WordPress plugin, feedless page watching, email digests
5. Public bundle export/import, forking, one-click Reclaim Cloud install

## Licence

MIT.
