---
title: Publishing
order: 6
---

# Publishing an aggRSSive

Every public aggRSSive has a page, under *aggRSSives*, with everything needed to republish it.

## Related posts

Under each item on an aggRSSive's page there is a small *related posts* link. Open it and aggRSSive lists the closest posts in meaning from the whole collection, whatever feed they came from, using the same local model as meaning rules. It is a way to follow a thread across feeds, and a quick check on whether a source you don't have yet is worth adding. Items are analysed a few minutes after they arrive; until then the link says so. The same link appears in course launches, unless the platform's settings turn it off.

## Feed your site (embed)

Copy the one line under **Feed your site** and paste it into any web page, WordPress post (in a Custom HTML block), or course page that accepts HTML:

```html
<script src="https://YOUR-SITE/embed/abcd1234.js"></script>
```

The list renders where the tag sits and updates itself. Attributes on the tag adjust it:

| Attribute | Effect |
|---|---|
| `data-n="8"` | number of items |
| `data-desc="0"` | no descriptions; `data-desc="full"` shows full text instead of a short excerpt |
| `data-img="0"` | hide images |
| `data-src="0"` | hide source names |
| `data-date="0"` | hide dates |
| `data-theme="dark"` or `"auto"` | colours |
| `data-target="#my-div"` | render into an element of your choosing |

If a site strips scripts, use the **iframe** version shown under *Options* instead.

## WordPress

Download the **aggRSSive block plugin** (the link is under *Options* on any aggRSSive's page, or at `/wordpress/aggrssive-embed.zip`), upload it under *Plugins → Add New → Upload Plugin*, and set your aggRSSive site's address once under *Settings → aggRSSive*. After that:

- add the **aggRSSive** block to any post or page and enter the aggRSSive's code (the part after `/bundles/` in its address); the block settings cover item count, descriptions, images, dates, theme and script-or-iframe, with a live preview in the editor;
- or use the shortcode anywhere shortcodes work: `[aggrssive slug="abcd1234" n="8" desc="none" theme="auto"]`.

The plugin adds no styling of its own beyond the list's; it emits the same script tag as *Feed your site*, so anything that works there works in WordPress. Multisite networks can network-activate it and set the site address per site.

## Subscribe

Each aggRSSive is itself a feed. **RSS**, **Atom** and **JSON Feed** links are on its page, so anyone can follow it in a reader or a podcast app, and anyone can add it to *their* aggRSSive as a source. There is also an **OPML** of its sources, for people who would rather take the feeds than the bundle.

Beside every feed and OPML address on the site there is a small copy button. Click it and the full address is on your clipboard, ready to paste into a reader, a podcast app or another aggRSSive. The icon beside the link says what it is: the feed glyph for RSS and Atom, a list for OPML, braces for JSON.

OPML is available for more than bundles. Any tag page and any classification heading offers **OPML of these sources**, *Find feeds* and *Sources* offer **OPML of everything**, and a bookmark list or a watched page has an **RSS** of its own, since it has no feed elsewhere. In OPML exports, sources that have no feed of their own are listed by their aggRSSive feed address, so the file works in any reader.

## Podcasts

Episodes keep their audio. On the aggRSSive's page, in embeds and in courses each episode has a player, and the bundle's RSS carries the enclosures, so a podcast app can subscribe to a bundle of shows as one show. See [For podcasters](podcasters).

## By email

Signed in, any aggRSSive's page offers **By email**: choose *every day* or *every week* and new items arrive at your account's address, with each item's source, your notes, and a short excerpt. Nothing is sent for a period with no new items, so a quiet list is a quiet inbox. Daily digests go out in the morning (UTC), weekly ones on Mondays; every mail has a one-click unsubscribe link, and the choice can be changed on the aggRSSive's page any time. The feature appears once a site admin has set up outgoing mail (see [Hosting](hosting)).

## In a course (LTI)

Instructors add an aggRSSive to a course from inside their platform: see [Moodle and other LMSs: for instructors](lti-instructors). Nothing is copied; the course shows the live list.

## JSON API

For anything custom: `https://YOUR-SITE/b/abcd1234.json` returns the current items with source, date, excerpt and image. Add `?n=20` for more, `&content=1` for full text. Cross-origin requests are allowed.
