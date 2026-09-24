# aggRSSive

Collect feeds. Tag them together. Filter them down. Bundle them into an *aggRSSive* and republish it anywhere: as embed code for any web page, as a feed of its own, or as a live LTI resource inside Moodle and other learning platforms.

A second edition of a tool first built at UBC in 2005 with Magpie RSS, Feed2JS and Freetag. Same idea, twenty years of better parts.

## What it does today

- **Sources**: paste any URL and aggRSSive finds the feed (RSS, Atom, JSON Feed). Import an OPML file to bring in a whole reader's worth. Polls on a schedule with conditional requests; dead feeds back off automatically.
- **Tags**: a shared folksonomy. Anyone can tag any source; OPML folders become tags.
- **Heart-Cart**: tick sources anywhere in the site, then turn the cart into a new aggRSSive or add it to one you have.
- **Rules**: include/exclude by keyword, phrase or regex on title, text, author, URL or category. Rules on a source apply everywhere; rules on a bundle apply to that bundle. Exclude always wins. Dedupe and a max-age window are built in.
- **Curation**: pin, hide and annotate individual items in a bundle. Pinning overrides the rules.
- **Outputs** for every public bundle: a `<script>` embed (with iframe fallback), RSS, Atom, JSON Feed, a JSON API, and OPML of the sources.
- **Classification**: Library of Congress and ISCED-F 2013 headings alongside tags; *Find feeds* searches and browses both; one click makes an aggRSSive from a tag or heading.
- **Suggestions**: tag proposals from the shared vocabulary and the feed's own categories; with an Anthropic API key, "ask aggRSSive (GenAI)" proposes tags and classification. Proposals only; a person accepts, edits or rejects.
- **Starter collections**: curated, liveness-verified feed sets (open education, teaching and learning, libraries, the open web, Indigenous knowledge, gender equity, intercultural perspectives) importable by a site admin with tags and classification attached.
- **Sharing**: every public aggRSSive can be copied into your own; bundles are feeds, so they can be sources for other bundles.
- **Accounts and roles**: local email/password, GitHub and Google sign-in when configured; regular users, site admins and full admins; first account is a full admin.
- **Help**: user documentation lives in `aggrssive/docs/` and renders in the app at `/help`.

## Moodle and other LMSs (LTI 1.3 Advantage)

aggRSSive is an LTI 1.3 tool with Deep Linking. An admin registers it once per platform at `/lti`; instructors then add any public aggRSSive to a course with *External tool → Select content*, choosing how many items to show and whether to include descriptions and images. The list stays live.

- **Moodle**: *Site administration → Plugins → External tool → Manage tools*, paste `https://<your-host>/lti/register` into *Tool URL*, click *Add LTI Advantage*. Done.
- **Other platforms**: `/lti` lists the login, launch, JWKS and deep-linking URLs, and has a form to paste the platform's details back in.

Launch state is kept server-side (one-time, ten-minute TTL) rather than in a cookie, so launches work inside LMS iframes where third-party cookies are blocked. The tool's RSA key is generated on first start at `LTI_KEY_PATH` (`/data/lti_private_key.pem` in Docker).

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

## Run it on Reclaim Cloud

Every push to `main` builds `ghcr.io/blamb/aggrssive:latest` (see `.github/workflows/image.yml`). In the Reclaim Cloud dashboard:

1. **New Environment → Custom** (Docker), **Select Image → Custom → Add New Image**, name `ghcr.io/blamb/aggrssive`, tag `latest`.
2. **Variables**: `SECRET_KEY` (long random string), `BASE_URL` (`https://<env>.<region>.reclaim.cloud`), `JELASTIC_EXPOSE=8000`.
3. Turn on **Built-In SSL**; leave Public IPv4 off. The `/data` volume is picked up from the image automatically.
4. Name the environment and **Create**.

To update after a new push: environment → the container's **Redeploy** action, keep tag `latest`. The `/data` volume, and therefore the database, is kept.

If your Moodle is on the same Reclaim Cloud account, two quirks apply: inside the platform, sibling environments resolve to private addresses that don't serve HTTPS, and the public load balancer is unreachable from inside. Add `DNS_OVERRIDES=<moodle-host>=http://<moodle node's private IP>` to the variables so aggRSSive reaches Moodle over the private network (find the IP in the Moodle node's `MASTER_IP` variable, or with `getent hosts <moodle-host>` from aggRSSive's Web SSH). For the reverse direction, paste aggRSSive's public key into the Moodle tool settings (*Public key type: RSA key*); the key is shown at `/lti`.

The base image is pinned to Debian 12 (`python:3.13-slim-bookworm`) on purpose: Reclaim runs custom containers as system containers and rejects Debian 13.

## Tests

```bash
.venv/bin/pytest
```

## Roadmap

1. ~~Sources, tags, bundles, rules, embed and feed outputs~~
2. ~~LTI 1.3 Advantage: Deep Linking picker and live resource inside Moodle; deploy to Reclaim Cloud~~
3. ~~Classification frameworks, GenAI tag and classification proposals, roles, in-app help, starter collections, forking~~
3b. Local embeddings for semantic filtering; plain-language item-level rules
4. Manual bookmarks, platform adapters (YouTube, Mastodon, Bluesky, arXiv, Zotero, Hypothesis...), bundles as sources, WordPress plugin, feedless page watching, email digests
5. Public bundle export/import, forking, one-click Reclaim Cloud install

## Licence

MIT.
