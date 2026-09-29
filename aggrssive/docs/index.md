---
title: Getting started
order: 1
---

# Getting started with aggRSSive

aggRSSive collects feeds, lets a group tag and classify them together, and turns any selection into a **bundle**: a live, filtered list to embed on a web page, subscribe to as a feed, or drop into a course in Moodle, Canvas or any other LTI platform. (Around here a bundle is sometimes called an aggRSSive, after the site. Same thing.)

It is a rebuild of a tool from UBC in 2005. Novak Rogic was its architect, it ran on Magpie RSS, Alan Levine's Feed2JS and Freetag, and two co-op students, Tyler P and Enej B, did much of the building. That one collected and republished; this one also filters, which is the part we never got working.

## The five-minute tour

1. **Find feeds.** *Find feeds* in the menu shows every source anyone has added, browsable by tag and by classification heading, and searchable by what feeds publish: type a subject and aggRSSive ranks feeds by their posts. Tick the ones you want; they collect in the **♥ Heart-Cart** at the bottom right.
2. **Add feeds.** *+ Add feed* takes any web address (a blog, a journal, a podcast, a YouTube channel, a Mastodon or Bluesky account, a Zotero group, a Hypothesis user) and finds its feed. Or import an OPML file from your feed reader. For single pages, keep a **Bookmarks** list: hand-picked, described for you, bundled like a feed. A page with no feed can be watched for new links or changes.
3. **Make a bundle.** From the Heart-Cart, name your bundle and click *Create*. It is live at once.
4. **Filter and curate.** On the bundle's *edit* page, add rules: keywords, a *meaning* ("assessment and grading practices"), or *plain language* for the GenAI to judge. Pin the items that matter, hide the ones that don't, add a note. *Feeds like these* suggests more sources that fit.
5. **Publish.** Every public bundle has embed code, RSS, Atom and JSON feeds, an email digest, and a place in any course via *External tool → Select content*. A bundle of podcasts is itself a show, with episodes that play wherever it is embedded; see [For podcasters](podcasters).

## Words used here

- **Feed**: a source of posts that updates itself (RSS, Atom, JSON Feed). Podcasts, YouTube channels and Mastodon accounts are feeds too.
- **Bundle**: a set of feeds you choose, filtered by rules, with a page, a feed and embed code of its own. Around here also called an aggRSSive.
- **Topic bundle**: a bundle with no fixed feeds; its rules sift every feed in the collection.
- **Tag**: a word anyone can put on a feed. **Heading**: a fixed classification (Library of Congress or ISCED-F) a feed is filed under.
- **Rule**: a filter on a bundle or a feed. **Meaning rule**: a description the local model compares posts to. **Plain-language rule**: a sentence the GenAI judges each post by.
- **Heart-Cart**: the box at the bottom right where ticked feeds collect until you name them as a bundle.
- **Bookmark list**: a feed you fill by hand, one page at a time. **Watched page**: a page with no feed, checked for new links or changes.
- **Embed**: the one-line script or iframe that shows a bundle on any web page. **OPML**: the file format feed readers use to swap lists of feeds.

## Where things are

| Menu item | What's there |
|---|---|
| **Find feeds** | Search, tags, classification, and the Heart-Cart |
| **Bundles** | Bundles: yours and everyone's public ones |
| **Bookmarks** | Hand-picked pages, in lists that bundle like feeds |
| **+ Add feed** | Add one feed or import many |
| **Help** | These pages |
| **Admin** | (site and full admins) LTI platforms and their settings, starter collections, users, sign-ups |

## Tips

A dashed box near the top of most pages, marked with a small feed icon, offers a hint that fits where you are: ↻ shows another, × hides tips on that page for a month, and *more* opens the help page behind it. Turn them off under your name → Account. Blue-edged **key tips** beside the trickier forms (rules, strictness, classification, the bookmarklet, LTI settings) are always shown. Those are the places people ask about.

## Accounts

Anyone with an account can add sources, tag and classify them, and build and publish bundles. No email to spare: *try it without an account* gives you an anonymous one with a secret link, claimable later. Sources, tags and classification belong to the collection, not to one person. Your bundles are yours to edit; others can see and copy the public ones.

See [Roles](roles) for what site admins and full admins can do, and [Privacy](privacy) for exactly what the site keeps about you, which is little.
