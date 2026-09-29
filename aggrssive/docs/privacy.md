---
title: Privacy
order: 12
---

# What this site keeps about you

The short version: aggRSSive keeps what it needs to run your account and your lists, and nothing for its own sake. No analytics, no advertising, no trackers, no third-party scripts or fonts on any page. This page says exactly what is stored, what leaves the server, and what does not.

## Accounts

- **Regular account**: your email, your display name, and a scrambled (bcrypt-hashed) version of your password. Never the password itself.
- **GitHub or Google sign-in**: the same, plus the provider's identifier for you so you can sign in again. No access token is kept; aggRSSive cannot act on your GitHub or Google account.
- **Anonymous account**: a random secret link and a made-up address that goes nowhere. No name, no email, unless you claim the account later.
- **Instructor arriving from a course** (LTI): the platform's identifier for you, and your name and email if the platform sends them. Students are never recorded.
- **Display preferences** (tag order, tips on or off) and, if you ask for email digests, which aggRSSives and how often.

Deleting an anonymous account removes its aggRSSives. Deactivating any account stops sign-in; what it added to the shared collection stays, because the collection belongs to everyone here.

## Your lists

Sources, tags, classification, aggRSSives, rules, pins, hides and notes are the content of the site and are stored as such. A public aggRSSive, including its notes, is visible to anyone, in embeds and in courses; a private one is visible only to you. Bookmarks in a list are visible to anyone who can see the list.

## Cookies and browser storage

One cookie: a signed session ticket that says which account you are, for thirty days, readable only by this site. The Heart-Cart, dismissed tips and the like live in your own browser's storage and never reach the server. Inside a course frame, aggRSSive needs no cookie at all.

## What leaves the server

- **Feeds**: aggRSSive fetches the feeds and pages in the collection, identifying itself as aggRSSive. Nothing about any person goes with those requests.
- **GenAI features** (when a site admin has enabled them): the feed's title, description and recent item titles for tag and classification proposals; a rule's text and each judged item's title and short excerpt for plain-language rules. Nothing about accounts, nothing from private aggRSSives, and bookmark notes are never included. The provider's data-use terms apply to that text; the site admin chose the provider.
- **Meaning rules, related posts, feeds like these, topic aggRSSives**: run on this server's own small model. Nothing leaves.
- **Email digests**: sent to the address on your account, from the mail relay the site admin configured. No tracking pixels; the unsubscribe link identifies only the subscription.
- **Podcast episodes and images**: play and load from the host the feed pointed at, so that host sees the request, as it would for any player.

## Server logs

Like every web server, this one records each request (address, page, time, status) in a log that the hosting provider keeps for a limited time, and the hosting provider's own load balancer keeps its own. When an aggRSSive is embedded on another site or placed in a course, the reader's browser fetches the list from here, so those requests appear in the log too. The log is used for fixing problems, nothing else, and it is not joined to accounts.

## What is never done

No selling, sharing or renting of anything above. No profiles of readers. No data from courses about who read what. If any of this changes, this page changes first, and *What's new* says so.

Questions go to the person who runs this install; their name is on the Users page for admins, and usually on the home page.
