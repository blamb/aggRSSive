# Copy review: the site's own prose

**Status: all cosmetic, clearer and voice rows applied on 2026-09-28 (see git log for the commit). The other eleven help pages still await their full pass.**

Register: **work memo / short message**. Audience: colleagues at a university who add feeds and build lists, plus instructors who meet the tool inside a course. No source files have been edited.

How to read this: each row is one string, with its file and line as of commit 60316e1. **cosmetic** is punctuation, a word, or a stray parenthetical; **clearer** says the same thing more plainly or names the specific thing; **voice** changes what the line sounds like and wants a careful read. **keep** means the string is in scope and I propose no change. Where a page earns a wry line, it is marked *(the page's one wry line)* so there is never a second.

Things applied throughout, from the guide: plain declaratives; no rhetorical questions in UI text (there were seven); no self-deprecation in errors; em-dashes and parentheticals only where the sentence needs them; the collection belongs to the people using it, so "your" gives way to "the collection" where the thing is shared, and stays "your" for aggRSSives, bookmark lists and accounts, which are personal. Technical names (RSS, Atom, LTI, embed, bundle, OPML, JSON) stay. Navigation, buttons, table headers and tag names are untouched.

Revision pass run on every proposal: warm-up sentences cut, bow-tying last sentences cut, intensifying adverbs removed, sentences that only introduced the next one deleted. Proposals run about 15% shorter than the originals overall.

---

## Home (`aggrssive/templates/home.html`)

| Line | Before | After | Type |
|---|---|---|---|
| 4 | Collect. Tag. Filter. Remix. Republish. | *keep* | keep |
| 5 | aggRSSive gathers feeds from anywhere, lets you tag them together, filters them down to what matters, and hands you back a bundle you can embed on any site or subscribe to as a feed of its own. | Feeds from anywhere, tagged by everyone here, filtered to what matters, and handed back as a bundle: embed it, subscribe to it, or drop it into a course. | voice |
| 5 (new, after it) | *(none)* | A rebuild of the 2005 UBC original: Novak Rogic's architecture, Magpie RSS, Alan Levine's Feed2JS, Freetag, and two co-op students, T. and E., who have since gone on to more respectable careers. *(the page's one wry line)* | voice |
| 12 | · browse by subject too | · or browse by subject | cosmetic |
| 21 | Recent aggRSSives | *keep* | keep |

The credit line is the only place the site names the 2005 lineage. Novak Rogic is named as the original architect and Alan Levine for Feed2JS; the two co-op students appear as initials, T. and E., at your request that their full identities stay private. If initials still feel like too much, "two co-op students" alone reads fine.

## Footer and Heart-Cart (`aggrssive/templates/base.html`)

| Line | Before | After | Type |
|---|---|---|---|
| 48 | aggRSSive · second edition · source | aggRSSive · 2005, rebuilt 2026 · source | voice |
| 55 | *placeholder:* Name this aggRSSive | *keep* | keep |
| 63 | Sign in to make a bundle. | Sign in to turn the cart into an aggRSSive. | clearer |
| tip bar | Tip / more / ↻ / × | *chrome; see the unsure list* | — |

## Sign in and sign up (`login.html`, `signup.html`, `routes/auth_routes.py`)

| Line | Before | After | Type |
|---|---|---|---|
| login 20 | No account? Create one. | New here: create an account. | clearer (removes a rhetorical question) |
| signup 20 | Already have one? Sign in. | Already have an account: sign in. | clearer (removes a rhetorical question) |
| login 14, signup 14 | or | *keep* | keep |
| auth_routes 56 | Wrong email or password. | *keep* | keep |
| auth_routes 67 | Sign-ups are closed on this install. Ask the admin for an account. | Sign-ups are closed here. Ask an admin for an account. | cosmetic |
| auth_routes 75, 139 | Sign-ups are closed on this install. | Sign-ups are closed here. | cosmetic |
| auth_routes 78 | Password needs at least 8 characters. | *keep* | keep |
| auth_routes 80 | That email already has an account. | *keep* | keep |
| auth_routes 129 | Your account did not share an email address. | GitHub or Google did not share an email address, and aggRSSive needs one. Sign up with email instead. | clearer |

## Find feeds (`find.html`)

| Line | Before | After | Type |
|---|---|---|---|
| 6 | *placeholder:* a subject, a tag, a heading code, a site name… | a subject, a tag, a heading code, a site name | cosmetic |
| 8 | all {n} sources | *keep* | keep |
| 14 | No tags match. | *keep* | keep |
| 16 | No headings match. | *keep* | keep |
| 19 | Ranked by what they actually publish, not by their name or tags. {n} posts analysed, {m} still to go. | Ranked by what they publish, not by their name or tags. {n} posts analysed, {m} still to go. | cosmetic (adverb) |
| 28 | No analysed posts are about this yet. | Nothing analysed so far is about this. | clearer |
| 47 | No sources match. Add one? | No sources match. Add one. | clearer (removes a rhetorical question) |
| 54 | Words people gave feeds. Click one to see its feeds and bundle them. | Words people here gave feeds. Click one to see its feeds and bundle them. | cosmetic |
| 55 | No tags yet. | *keep* | keep |
| 59 | Two standard frameworks. Headings with nothing filed are folded away; expand a class to see its subclasses. | Library of Congress and ISCED-F. Headings with nothing filed are folded away; expand a class to see its subclasses. | clearer (names the specific thing) |

## Sources list (`sources.html`, `tags.html`, `classification.html`, `category.html`)

| Line | Before | After | Type |
|---|---|---|---|
| sources 7 | Imported {n} new feeds. They're being fetched now. | Imported {n} new feeds. Fetching them now. | cosmetic |
| sources 9 | *placeholder:* Search sources | *keep* | keep |
| sources 15 | Filed under {heading} and below | *keep* | keep |
| sources 33 | No sources yet. Add the first one. | *keep* | keep |
| sources 48 | Tick sources to collect them in the Heart-Cart, then turn the cart into an aggRSSive. | *keep* | keep |
| tags 5 | A shared vocabulary. Anyone can tag any source; tags are what make the collection browsable. | The collection's vocabulary. Anyone can tag any source, and the tags are how people find things. | voice |
| classification 5 | Two controlled frameworks sit alongside the free tags: the Library of Congress outline and UNESCO's ISCED-F fields of education. Counts include everything filed beneath a heading. | Two controlled frameworks beside the free tags: the Library of Congress outline, and UNESCO's ISCED-F fields of education. Counts include everything filed beneath a heading. | cosmetic |
| classification 17 | Headings with nothing filed yet are folded away; every heading is still available when classifying a source. | *keep* | keep |
| category 16 | No sources filed here yet. | *keep* | keep |

## Add a feed (`source_add.html`, `routes/sources.py`)

| Line | Before | After | Type |
|---|---|---|---|
| 6 | Paste any address: a blog, a journal, a podcast, a feed URL, or a YouTube channel or playlist, a Mastodon or Bluesky account, a Mastodon hashtag, a public Zotero group or library, or a Hypothesis user, group or tag. aggRSSive will find the feed. | Paste an address and aggRSSive finds the feed: a blog, a journal, a podcast, a YouTube channel or playlist, a Mastodon or Bluesky account, a Mastodon hashtag, a public Zotero group or library, a Hypothesis user, group or tag. | clearer |
| 8 | *placeholder:* https://example.edu/blog | *keep* | keep |
| 20 | *placeholder:* leave blank to use the page's own | *keep* | keep |
| 21, 34 | *placeholder:* comma, separated | *keep* | keep |
| 25 | Just one page, not a whole site? Bookmark it instead. | For a single page rather than a site, bookmark it instead. | clearer (removes a rhetorical question) |
| watch heading | Watch the page instead | *keep* | keep |
| watch radio 1 | New links — each article-like link on the page becomes an item the first time it appears (news pages, publication lists, event listings) | New links: each article-like link on the page becomes an item the first time it appears. For news pages, publication lists and event listings. | cosmetic (dash and parenthetical) |
| watch radio 2 | Changes — one item each time the page's text changes, saying what was added and removed (policies, syllabi, calls for papers) | Changes: one item each time the page's text changes, saying what was added and removed. For policies, syllabi and calls for papers. | cosmetic |
| 32 | (untitled) | *keep* | keep |
| routes/sources 79 | No feed found at that address. You can paste the feed URL directly, or watch the page itself (below). | No feed at that address. Paste the feed URL directly, or watch the page itself, below. | clearer |

## Source page (`source.html`, `routes/sources.py`)

| Line | Before | After | Type |
|---|---|---|---|
| 14 | *placeholder:* add tags, comma separated | *keep* | keep |
| 41 | Nothing is applied until you tick it. ✎ copies a suggestion into the box above so you can change it first. | Nothing is applied until you tick it. ✎ copies a suggestion into the box so you can change it first. | cosmetic |
| 43 | None pending. Suggestions come from tags already used here that match this feed, and from categories the feed declares; ✨ asks aggRSSive's GenAI for more. | None pending. Suggestions come from tags already in use here that fit this feed, and from categories the feed declares. ✨ asks aggRSSive's GenAI for more. | cosmetic |
| 56 | *placeholder:* type a code or subject: LB, 0111, 'open education'… | a code or a subject: LB, 0111, open education | cosmetic |
| 83 | None pending. ✨ asks aggRSSive's GenAI to propose Library of Congress and ISCED-F headings. / Set an API key to get GenAI proposals; until then, file sources by hand above. | None pending. ✨ asks aggRSSive's GenAI to propose Library of Congress and ISCED-F headings. / GenAI is off on this site, so file sources by hand above. | clearer |
| 91 | or use the bookmarklet from Bookmarks | *keep* | keep |
| 92 | Last fetch failed: {error} | *keep* | keep |
| 93 | Nothing fetched yet. Fetch now | *keep* | keep |
| 94 | Nothing bookmarked yet. | *keep* | keep |
| 108 | A watched page ({new links / changes}), checked on the normal schedule. | A watched page, {new links / changes}, checked on the normal schedule. | cosmetic |
| 111 | Last fetched {ago} · last success {ago} | *keep* | keep |
| 113 | A bookmark list: filled by hand, never polled. Last addition {ago}. | *keep* | keep |
| 115 | Apply everywhere this source is used. *(now a key tip)* | *see Tips* | — |
| 129 | *placeholder:* word, phrase, regex — or a description | word, phrase, regex, or a description | cosmetic |
| 131 | (meaning rules) | for meaning rules | cosmetic |
| 144 | *confirm:* Delete this source and its items? Bundles using it will lose it. | Delete this source and its items? aggRSSives using it lose it. | cosmetic (confirm dialogs keep their question) |
| routes 233 | Only the person who added a source, or a site admin, can delete it. | *keep* | keep |
| routes 136 | No such source | *keep* | keep |

## Bookmarks (`bookmarks.html`, `bookmark_add.html`, `routes/bookmarks.py`)

| Line | Before | After | Type |
|---|---|---|---|
| bookmarks 7 | A bookmark list is a source you fill by hand, one page at a time. It goes into aggRSSives, embeds and courses exactly like a feed. | A bookmark list is a source you fill by hand, one page at a time. It goes into aggRSSives, embeds and courses like any feed. | cosmetic (adverb) |
| bookmarks 20 | No lists yet. Make one on the right. | *keep* | keep |
| bookmarks 33 | Bookmark from anywhere | *keep* | keep |
| bookmarks 34 | ♥ aggRSSive this | *chrome; see the unsure list* | — |
| bookmarks 39 | *placeholder:* e.g. Readings for week 3 | Readings for week 3 | cosmetic |
| bookmarks 43 | Lists are shared like feeds: anyone can bundle them, only you (and site admins) add to them. | Lists are shared like feeds. Anyone can bundle them; only you and site admins can add to them. | cosmetic |
| add 7 | You need a bookmark list first. Make one, then come back. | *keep* | keep |
| add 10 | *placeholder:* https://example.edu/an-article | *keep* | keep |
| add 15 | Here's what the page says about itself. Change anything, then save. | What the page says about itself. Change anything, then save. | cosmetic |
| add 22 | *placeholder:* why this matters, shown with the bookmark | why this matters; shown with the bookmark | cosmetic |
| feeds/bookmarks error | Could not read the page ({error}). Fill in the details yourself. | Could not read the page: {error}. Fill in the details yourself. | cosmetic |
| feeds/bookmarks error 2 | Could not make sense of the page ({error}). | Could not make sense of the page: {error}. Fill in the details yourself. | clearer |
| routes 36 | No such bookmark list | *keep* | keep |
| routes 38 | Only the list's owner (or a site admin) can change it | Only the list's owner or a site admin can change it | cosmetic |
| routes 54 | Give the list a name | *keep* | keep |

## aggRSSives list and page (`bundles.html`, `bundle.html`, `routes/bundles.py`)

| Line | Before | After | Type |
|---|---|---|---|
| bundles 5 | Bundles of sources, filtered and curated, each with its own feed and embed code. | *keep* | keep |
| bundles 11 | None yet. Go to Sources, tick a few, and create one from the Heart-Cart. | None yet. Go to Find feeds, tick a few sources, and create one from the Heart-Cart. | clearer (the page is now Find feeds) |
| bundles 18 | Nothing public yet. | *keep* | keep |
| bundle 25 | Nothing passes the filters yet. | *keep* | keep |
| bundle 31 | Paste this where you want the list to appear: | *keep* | keep |
| bundle 36 | Add attributes to the script tag: | *keep* | keep |
| bundle 46 | WordPress? Install the aggRSSive block plugin once, set the site address under Settings → aggRSSive, then add the aggRSSive block with the code {slug}, or the shortcode [aggrssive slug="{slug}"]. | On WordPress, install the aggRSSive block plugin once, set the site address under Settings → aggRSSive, then add the aggRSSive block with the code {slug}, or the shortcode [aggrssive slug="{slug}"]. | clearer (removes a rhetorical question) |
| bundle 47 | Or an iframe, for sites that block scripts: | *keep* | keep |
| bundle 61 | New items go to {email} {every day/week}; quiet periods send nothing. / New items to {email}, only when there are some. | New items go to {email} {every day/week}. A quiet week sends nothing. / New items to {email}, only when there are any. | cosmetic |
| bundle 66 | A private copy with the same sources, rules and settings, for you to change. | A private copy with the same sources, rules and settings. Change it however you like; the original is untouched. | clearer |
| routes 19, 118, 142 | No such aggRSSive | *keep* | keep |
| routes 61, 66 | No such tag / No such heading | *keep* | keep |
| routes 69 | Say which tag or heading | *keep* | keep |
| routes 159 | Not yours to edit | *keep* | keep |
| routes 210 | A rule needs a kind, a field and a pattern. | *keep* | keep |
| routes 212 | Meaning rules are switched off on this site (EMBEDDINGS_ENABLED). | Meaning rules are switched off on this site. An admin can turn them on with EMBEDDINGS_ENABLED. | cosmetic |
| routes 214 | Plain-language rules need GenAI enabled on this site. | *keep* | keep |

## Edit page (`bundle_edit.html`)

| Line | Before | After | Type |
|---|---|---|---|
| 15 | Add more from Find feeds via the Heart-Cart. | Add more from Find feeds, via the Heart-Cart. | cosmetic |
| 18 | Not in this aggRSSive yet, but writing about the same things as the items it includes. Tick to add. | Not in this aggRSSive, but writing about the same things as the items it includes. Tick to add. | cosmetic |
| 32 | Exclude rules always win. An item must match **all**/**any** include rule(s). No include rules means everything gets in. | *keep* | keep |
| 38 | No rules. Everything from these sources is included. | *keep* | keep |
| 44 | *placeholder:* word, phrase, regex — or a description for meaning / plain-language rules | word, phrase, regex, or a description for a meaning or plain-language rule | cosmetic |
| 49 | Meaning rules compare each item to your description with a local model — "assessment and grading practices in higher education" — and take a moment to analyse new items. Plain-language rules ask aggRSSive's GenAI once per item — "only posts about open pedagogy; drop job ads and event announcements" — and cost a fraction of a cent each. Strictness applies to meaning rules. See Help → Building an aggRSSive. | Meaning rules compare each item to a description ("assessment and grading practices in higher education") with a model that runs on this server, and take a few minutes to catch up with new items. Plain-language rules ask aggRSSive's GenAI once per item ("only posts about open pedagogy; drop job ads and event announcements") and cost a fraction of a cent each. Strictness applies to meaning rules. See Help → Building an aggRSSive. | clearer (dashes to parentheses; "takes a moment" was untrue) |
| 64 | *placeholder:* note for readers | *keep* | keep |
| 75 | Recent items from your sources that didn't make it, and why. "Pending" means a meaning or plain-language rule hasn't analysed the item yet; it will within a few minutes. Pin one to force it in. | Recent items from these sources that didn't make it, and why. *(the rest now lives in the key tip beside it; cut here)* | clearer (removes duplication with the key tip) |
| 98 | Only items newer than [days] days | *keep* | keep |
| 105 | *confirm:* Delete this aggRSSive? Its embed code and feeds will stop working. | Delete this aggRSSive? Its embed code and feeds stop working. | cosmetic |

## Account (`account.html`, `routes/admin.py`)

| Line | Before | After | Type |
|---|---|---|---|
| 12 | Bigger tags are used by more sources either way. | Size still shows how many sources carry a tag. | clearer |
| 13 | Show a rotating tip on each page (key tips beside forms stay either way) | Show a tip on each page. Key tips beside forms stay either way. | cosmetic |
| 16 | *placeholder:* leave blank to keep | *keep* | keep |
| routes 129 | New password needs at least 8 characters | *keep* | keep |
| routes 131 | Current password is wrong | *keep* | keep |

## Admin (`admin.html`, `admin_users.html`, `admin_collections.html`, `routes/admin.py`)

| Line | Before | After | Type |
|---|---|---|---|
| admin 7 | Register Moodle and other learning platforms; registration URLs and keys. | Register Moodle and other learning platforms, and change what each one gets. | clearer |
| admin 8 | Curated feed collections you can import in one click. | Curated, checked collections of feeds, imported in one click. | cosmetic |
| admin 10 | Create accounts, change roles, deactivate. | *keep* | keep |
| admin 15 | anyone can create an account | *keep* | keep |
| admin 18 | Configured ({host}). People subscribe on any aggRSSive's page. / Off. Set SMTP_HOST and SMTP_FROM in the environment to enable — see Hosting. | Configured, via {host}. People subscribe on any aggRSSive's page. / Off. Set SMTP_HOST and SMTP_FROM in the environment; see Hosting. | cosmetic |
| admin 20 | Test digest sent to {email}. / No public aggRSSive to send yet. | *keep* | keep |
| admin 21 | Enabled. The ✨ buttons are live. / Off. Set ANTHROPIC_API_KEY in the environment to enable — see Help. | On. The ✨ buttons are live. / Off. Set ANTHROPIC_API_KEY in the environment; see Help. | cosmetic |
| admin 24 | What each role can do: Help → Roles. | *keep* | keep |
| users 32 | Deactivated people can't sign in; everything they added stays. Roles are explained in Help → Roles. | Deactivated people can't sign in. Everything they added stays with the collection. Roles are explained in Help → Roles. | voice |
| users 40 | *placeholder:* they change it under their name → Account | they change it under their name → Account | keep |
| routes 42 | Role must be valid and password at least 8 characters | Choose a role and a password of at least 8 characters | clearer |
| routes 44 | That email already has an account | *keep* | keep |
| routes 56 | You can't demote or deactivate yourself | *keep* | keep |
| collections 6 | Curated sets of feeds that ship with aggRSSive. Every feed was checked to be alive when the collection was built. Importing adds the feeds with their tags and classification; feeds you already have are left alone, so importing again is safe. | Sets of feeds that ship with aggRSSive, every one checked alive when the set was built. Importing adds them with their tags and classification. Feeds already in the collection are left alone, so importing twice is safe. | clearer |
| collections 11 | {n} feeds · {m} already in your collection | {n} feeds · {m} already here | cosmetic |
| collections 19 | No collections shipped with this version. | *keep* | keep |
| routes 108 | No such collection | *keep* | keep |

## LTI admin (`lti_admin.html`)

| Line | Before | After | Type |
|---|---|---|---|
| 7 | Register this aggRSSive as an LTI 1.3 tool once per platform. Instructors then add any public aggRSSive to a course with External tool → Select content, and the list stays live. | *keep* | keep |
| 16 | *confirm:* Remove this platform? Launches from it will stop working. | Remove this platform? Launches from it stop working. | cosmetic |
| 32 | None yet. | *keep* | keep |
| 36–39 | *(the four Moodle steps)* | *keep* | keep |
| 45 | Moodle verifies aggRSSive's signatures by fetching the keyset URL above. If the two sites live on the same cloud (e.g. both on Reclaim Cloud) that fetch can fail, because the platform resolves this hostname to a private address. Fix: in Moodle, edit the registered tool, set Public key type to RSA key and paste this. Nothing else changes. | Moodle checks aggRSSive's signatures by fetching the keyset URL above. When both sites live on the same cloud, Reclaim Cloud for instance, that fetch can fail because the platform resolves this hostname to a private address. The fix: in Moodle, edit the registered tool, set Public key type to RSA key, and paste this. Nothing else changes. | cosmetic |
| 49 | Give the platform these values, then paste what it gives you back into the form on the right. | *keep* | keep |
| 57 | *placeholder:* e.g. TRU Moodle | TRU Moodle | cosmetic |
| settings form labels | *(the six option labels)* | *see the unsure list* | — |

## LTI picker, launch, registration, error (`lti_pick.html`, `lti_resource.html`, `lti_registered.html`, `lti_error.html`)

| Line | Before | After | Type |
|---|---|---|---|
| pick 23 | Hi {name}. *(then the picker key tip)* | *keep* | keep |
| pick 26 | *placeholder:* Search aggRSSives… | Search aggRSSives | cosmetic |
| pick 34 | No public aggRSSives yet. Make one at {site}, then come back. | *keep* | keep |
| pick 46 | Want your own list here? Create it at aggRSSive and mark it public. | To offer your own list here, create it at aggRSSive and mark it public. | clearer (removes a rhetorical question) |
| resource 41 | Nothing passes this aggRSSive's filters yet. | *keep* | keep |
| resource 44 | {title} · via aggRSSive · RSS | *keep* | keep |
| registered 5 | ✓ aggRSSive is registered with {platform} | *keep* | keep |
| registered 6 | You can close this window. In Moodle, the tool now appears under External tool; activate it if it shows as pending, then add an aggRSSive to any course with Add an activity → External tool → aggRSSive → Select content. | Close this window. In Moodle the tool now appears under External tool; activate it if it shows as pending. Instructors add an aggRSSive to a course with Add an activity → External tool → aggRSSive → Select content. | cosmetic |
| error 4 | aggRSSive couldn't complete this launch | *keep* | keep |
| service (various) | Launch state is missing or was already used / The platform did not say where to return the selection. / This aggRSSive no longer exists or has been made private. | *keep* | keep |

## Digests and related posts (`digest_unsubscribed.html`, `related.html`, `digest.py`)

| Line | Before | After | Type |
|---|---|---|---|
| unsub 6 | You will no longer get email digests of {title}. | Done. No more email digests of {title}. | voice |
| unsub 6 | That link has already been used, or was not valid. Nothing changed. | That link was already used, or was not valid. Nothing changed. | cosmetic |
| unsub 7 | Digests can be turned back on from the aggRSSive's page when you are signed in. | Turn them back on from the aggRSSive's page, signed in. | clearer |
| related 1 | Not analysed yet; try again in a few minutes. | *keep* | keep |
| related 2 | Nothing close enough in the collection yet. | *keep* | keep |
| digest.py footer | You get this {every day/week} because you asked for it on aggRSSive. Unsubscribe: {url} | You asked for this {every day/week} on aggRSSive. Unsubscribe: {url} | cosmetic |
| digest.py subject | {title}: {n} new item(s) | *keep* | keep |

## Error pages and access messages (`error.html`, `auth.py`, `help_routes.py`, `classify.py`, `tags.py`, `digests.py`)

| Line | Before | After | Type |
|---|---|---|---|
| error 7 | Back home | *keep* | keep |
| auth 59 | Sign in required | *keep* | keep |
| auth 65 | Site admins only | *keep* | keep |
| auth 71 | Full admins only | *keep* | keep |
| help_routes 19 | No such help page | *keep* | keep |
| classify 26 | No such category | No such heading | clearer (the UI says heading) |
| tags 25 | No such tag | *keep* | keep |
| digests 51 | Email is not configured | Email is not configured on this site | cosmetic |

## Tips (`aggrssive/tips.py`)

The tips were written last week in roughly this register, so most rows are keep. The changes:

| Tip | Before | After | Type |
|---|---|---|---|
| Find, 1 | Search Find feeds with a whole phrase, not a keyword: "students using generative AI to write essays" finds far more than "AI". | Search with a whole phrase, not a keyword. "Students using generative AI to write essays" finds far more than "AI". | cosmetic |
| Find, 2 | Feeds writing about this ranks sources by what they actually publish, not by their name or tags. It is the fastest way to find a feed you did not know existed. | Feeds writing about this ranks sources by what they publish, not by their name or tags. It is the quickest way to find a feed you did not know existed. | cosmetic |
| sources, 4 | A feed that mixes what you want with what you don't? Put an exclude rule on the source itself and it applies everywhere that feed is used. | For a feed that mixes what you want with what you don't, put an exclude rule on the source itself. It applies everywhere that feed is used. | clearer (removes a rhetorical question) |
| bundles, 7 | Like someone's aggRSSive? Copy to my aggRSSives gives you a private copy with the same sources and rules to adapt. | Copy to my aggRSSives, on anyone's public list, gives you a private copy with the same sources and rules to adapt. | clearer (removes a rhetorical question) |
| bundles, 12 | Prefer email? By email on an aggRSSive's page sends you its new items daily or weekly, and nothing at all when there is nothing new. | By email, on an aggRSSive's page, sends you its new items daily or weekly, and nothing when there is nothing new. | clearer (removes a rhetorical question) |
| lti, 3 | Moodle on the same cloud as aggRSSive? Paste the public key into the tool settings (Public key type: RSA key) instead of relying on the keyset URL. | When Moodle shares a cloud with aggRSSive, paste the public key into the tool settings (Public key type: RSA key) instead of relying on the keyset URL. | clearer (removes a rhetorical question) |
| general, 2 | Tired of tips? Turn them off under your name → Account, or hide them on a page with ×. | Tips can be turned off under your name → Account, or hidden on a page with ×. | clearer (removes a rhetorical question) |
| admin, 2 | Starter collections are verified, tagged and classified, and deliberately include Indigenous, gender-equity and Global South sources. Import one, then prune. | Starter collections are checked, tagged and classified, and make room on purpose for Indigenous, gender-equity and Global South sources. Import one, then prune. | voice |
| key tip "watch" | No feed? Watch the page. … | No feed on the page: watch it instead. … *(rest unchanged)* | clearer (removes a rhetorical question) |
| key tip "same-cloud" | Same cloud as your LMS? Registration or launches failing with … | On the same cloud as your LMS, registration or launches failing with … | clearer (removes a rhetorical question) |

All other tips and key tips: keep.

## Help: Getting started (`aggrssive/docs/index.md`), in full

| Line | Before | After | Type |
|---|---|---|---|
| 8 | aggRSSive collects feeds, lets a group tag and classify them together, and turns any selection into an aggRSSive: a live, filtered bundle you can embed on a web page, subscribe to as a feed, or drop into a course in Moodle, Canvas or any other LTI platform. | aggRSSive collects feeds, lets a group tag and classify them together, and turns any selection into an aggRSSive: a live, filtered bundle to embed on a web page, subscribe to as a feed, or drop into a course in Moodle, Canvas or any other LTI platform. | cosmetic |
| 8 (new) | *(none)* | It is a rebuild of a tool from UBC in 2005. Novak Rogic was its architect, it ran on Magpie RSS, Alan Levine's Feed2JS and Freetag, and two co-op students, T. and E., did much of the building. That one collected and republished; this one also filters, which is the part we never got working. *(the page's one wry line)* | voice |
| 10 | The five-minute tour | *keep* | keep |
| 12 | Find feeds. Find feeds in the menu shows every source anyone has added, browsable by tag and by classification heading, and searchable by what feeds actually publish (type a subject; aggRSSive ranks feeds by their posts). Tick the ones you want; they collect in the ♥ Heart-Cart at the bottom right. | Find feeds. Find feeds in the menu shows every source anyone has added, browsable by tag and by classification heading, and searchable by what feeds publish: type a subject and aggRSSive ranks feeds by their posts. Tick the ones you want; they collect in the ♥ Heart-Cart at the bottom right. | cosmetic |
| 13 | Add feeds. + Add feed takes any web address — a blog, a journal, a podcast, a YouTube channel, a Mastodon or Bluesky account, a Zotero group, a Hypothesis user — and finds its feed. Or import an OPML file from your feed reader. For single pages, keep a Bookmarks list: hand-picked, described automatically, bundled like a feed. | Add feeds. + Add feed takes any web address (a blog, a journal, a podcast, a YouTube channel, a Mastodon or Bluesky account, a Zotero group, a Hypothesis user) and finds its feed. Or import an OPML file from your feed reader. For single pages, keep a Bookmarks list: hand-picked, described for you, bundled like a feed. A page with no feed can be watched for new links or changes. | clearer |
| 14 | Make an aggRSSive. From the Heart-Cart, name your bundle and click Create. It's live immediately. | Make an aggRSSive. From the Heart-Cart, name your bundle and click Create. It is live at once. | cosmetic |
| 15 | Filter and curate. On the bundle's edit page, add rules — keywords, a meaning ("assessment and grading practices"), or plain language for the GenAI to judge — pin the items that matter, hide the ones that don't, add a note. Feeds like these suggests more sources that fit. | Filter and curate. On the bundle's edit page, add rules: keywords, a meaning ("assessment and grading practices"), or plain language for the GenAI to judge. Pin the items that matter, hide the ones that don't, add a note. Feeds like these suggests more sources that fit. | cosmetic |
| 16 | Publish. Every public aggRSSive has embed code, RSS/Atom/JSON feeds, and can be added to a course with External tool → Select content. | Publish. Every public aggRSSive has embed code, RSS, Atom and JSON feeds, an email digest, and a place in any course via External tool → Select content. | clearer |
| 18–28 | Where things are *(table)* | *keep* | keep |
| 30 | A dashed Tip box near the top of most pages offers a short hint that fits where you are; ↻ shows another, × hides tips on that page for a month, and more opens the help page behind it. Turn them off altogether under your name → Account. Blue-edged key tips beside the trickier forms (rules, strictness, classification, the bookmarklet, LTI settings) are always shown, because those are the places people most often ask about. | A dashed Tip box near the top of most pages offers a hint that fits where you are: ↻ shows another, × hides tips on that page for a month, and more opens the help page behind it. Turn them off under your name → Account. Blue-edged key tips beside the trickier forms (rules, strictness, classification, the bookmarklet, LTI settings) are always shown. Those are the places people ask about. | cosmetic |
| 34 | Anyone with an account can add sources, tag and classify them, and build and publish aggRSSives. Everything shared — sources, tags, classification — belongs to the collection, not to one person. Your aggRSSives are yours to edit; others can see and reuse the public ones. | Anyone with an account can add sources, tag and classify them, and build and publish aggRSSives. Sources, tags and classification belong to the collection, not to one person. Your aggRSSives are yours to edit; others can see and copy the public ones. | cosmetic |
| 36 | See Roles for what site admins and full admins can do. | *keep* | keep |

## Help: the other pages, openers only

The remaining eleven help pages are in the same register already and mostly hold procedure. I read them all and propose only their opening lines here; if you accept the approach, I will do the full pass on them as a second table.

| Page | Before | After | Type |
|---|---|---|---|
| sources.md 8 | A source is a feed: RSS, Atom or JSON Feed. Sources are shared — once anyone adds one, everyone can tag it, classify it and put it in a bundle. | A source is a feed: RSS, Atom or JSON Feed. Sources are shared. Once anyone adds one, everyone can tag it, classify it and put it in a bundle. | cosmetic |
| bookmarks.md 8 | Not everything worth sharing comes from a feed. … A reading list for a week, a set of examples for an assignment, or the ten best things you read this month all fit. | *keep* | keep |
| tags-and-classification.md 8–10 | aggRSSive has two ways to describe a source, and they're deliberately different. Tags are free words, shared by everyone … Tags are quick, personal, and grow into the collection's own vocabulary. | aggRSSive has two ways to describe a source, and they are different on purpose. Tags are free words, shared by everyone … Tags are quick, and they grow into the collection's own vocabulary. | cosmetic ("personal" contradicts "shared") |
| bundles.md 8 | An aggRSSive is a bundle: a set of sources, rules that decide which of their items get through, and your own curation on top. It updates itself as the feeds do. | *keep* | keep |
| publishing.md 8 | Every public aggRSSive has a page — aggRSSives → its name — with everything needed to republish it. | Every public aggRSSive has a page, under aggRSSives, with everything needed to republish it. | cosmetic |
| lti-instructors.md 8 | Once an admin has connected aggRSSive to your platform (see the admin guide), adding a list to a course takes a minute and needs no account on aggRSSive. | *keep* | keep |
| lti-admin.md 8 | aggRSSive is an LTI 1.3 Advantage tool with Deep Linking. Register it once per platform; instructors then add any public aggRSSive to their courses with the platform's content picker. Registration is done by a site admin at Admin → LTI platforms. | *keep* | keep |
| genai.md 8 | aggRSSive can use a language model for the judgement calls that simple rules can't make: what a feed is about, which tags fit it, where it belongs in a classification. The features are off until a site admin adds an API key, and every one of them makes proposals only — a person accepts, edits or rejects each. | aggRSSive can use a language model for the judgement calls simple rules can't make: what a feed is about, which tags fit it, where it belongs in a classification. The features are off until a site admin adds an API key, and every one of them only proposes. A person accepts, edits or rejects each. | cosmetic |
| roles.md 8 | Three kinds of account. | *keep* | keep |
| hosting.md 8 | aggRSSive is a single container with one data volume. It runs anywhere Docker does; Reclaim Cloud is the reference setup. | *keep* | keep |
| changelog.md 8 | Newest first. Dates are when the change reached the main site. | Newest first. | clearer (there are no dates in the list) |

---

## Unsure: chrome or prose (left alone, listed for you)

- `base.html` tip bar: the word "Tip", the "more" link, ↻ and ×. Reads as chrome.
- `bookmarks.html` 34: the bookmarklet's button text "♥ aggRSSive this". It is a label people drag, so I treated it as a button.
- `lti_admin.html` settings form: the six option labels ("Show related posts under each item in launches", "Open item links in a new tab (off: navigate inside the platform's frame)", "Also carry the Deep Linking response in the return URL (needed by Moodle; turn off if a platform rejects long URLs)", "Frame height asked for", "Default items per launch", "Default descriptions"). They are form labels with explanations folded in; the parentheticals are the only prose-like part. If you want them touched, the second one becomes "Open item links in a new tab. Off: links open inside the platform's frame." and the third "Also carry the Deep Linking response in the return URL. Moodle needs it; turn off if a platform rejects long URLs."
- `bundle_edit.html` 32: "Exclude rules always win…" sits beside the rules list as a hint but is also, in effect, the rule of the feature. Kept as is.
- `source_add.html` 32: "(untitled)" as a candidate title. Data placeholder, not prose.
- `lti_pick.html` 23: "Hi {name}." A greeting inside a course frame. Kept; it is the one warm line in the picker.
- Category labels, framework names (Library of Congress Classification, ISCED-F 2013), rule field labels ("meaning (local model)", "plain language (GenAI)"), strictness names (loose, normal, strict), role names, frequency names ("every day", "every week"). All orientation text; untouched.
- Commit messages, code comments, the README, the WordPress plugin's own strings (readme.txt, block labels) and the CLAUDE.md notes: out of scope as stated, though the plugin's readme could use the same pass later.

## Rhetorical questions removed (seven in UI text, plus six in tips)

login 20, signup 20, find 47, source_add 25, bundle 46, lti_pick 46, and the key tips "watch" and "same-cloud"; tips sources-4, bundles-7, bundles-12, lti-3, general-2. Confirmation dialogs keep their question, since a confirm is one.

## Wry lines, one per page

Home (the credit line's "more respectable careers"), Getting started ("which is the part we never got working"). No others added; the tips already carry a light touch and none was added there.

## After approval

The template test suite (`.venv/bin/pytest`, 86 tests) exercises every page and several exact strings, so it is the check to run after edits. I expect about six tests to need their expected strings updated (the ones asserting "By email", "Feeds writing about this", "No such", "Nothing changed", the digest footer and the unsubscribe copy).
