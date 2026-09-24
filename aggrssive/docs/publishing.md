---
title: Publishing
order: 5
---

# Publishing an aggRSSive

Every public aggRSSive has a page — *aggRSSives → its name* — with everything needed to republish it.

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

## Subscribe

Each aggRSSive is itself a feed — **RSS**, **Atom** and **JSON Feed** links are on its page — so anyone can follow it in a reader, and anyone can add it to *their* aggRSSive as a source. There's also an **OPML** of its sources, for people who'd rather take the feeds than the bundle.

## In a course (LTI)

Instructors add an aggRSSive to a course from inside their platform: see [Moodle and other LMSs: for instructors](lti-instructors). Nothing is copied; the course shows the live list.

## JSON API

For anything custom: `https://YOUR-SITE/b/abcd1234.json` returns the current items with source, date, excerpt and image. Add `?n=20` for more, `&content=1` for full text. Cross-origin requests are allowed.
