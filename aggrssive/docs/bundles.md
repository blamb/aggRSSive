---
title: Building an aggRSSive
order: 4
---

# Building an aggRSSive

An **aggRSSive** is a bundle: a set of sources, rules that decide which of their items get through, and your own curation on top. It updates itself as the feeds do.

## Create one

Tick sources anywhere — the sources list, a tag page, a classification heading, a source's own page — and they collect in the **♥ Heart-Cart** at the bottom right. Give it a name and click **Create**, or choose one of your existing aggRSSives and click **Add**. Tag and heading pages also offer **Make an aggRSSive from these** to bundle everything listed.

You land on the bundle's *edit* page.

## The edit page

**Sources** — what's in the bundle. Remove with ×; add more via the Heart-Cart.

**Feeds like these** — feeds not yet in the bundle whose posts resemble the items it currently includes, worked out by the same local model as meaning rules. It follows the bundle: tighten the rules and the suggestions tighten with them. Tick the ones you want and click *Add ticked feeds*. The list appears once the bundle includes some analysed items.

**Rules** — filters. Each rule says *include* or *exclude*, which part of an item to look at (title, text, author, URL, category, or any), and a word, phrase or regular expression.

- *Exclude* rules always win.
- With no *include* rules, everything not excluded gets through.
- With *include* rules, an item must match **any** of them (the default) or **all** of them — choose under Settings.
- Regular expressions are for the fussy: `\bAI\b` matches "AI" but not "detail".

Two smarter kinds of rule, chosen from the same *field* menu:

- **Meaning (local model)** — write a description instead of a keyword: *"assessment and grading practices in higher education"*. Each item is compared to it by a small language model that runs on the server itself: free, private, no key. *Strictness* sets how close an item has to be: *loose* lets related items through, *strict* wants a close match; *normal* suits most lists. New items take a few minutes to be analysed; until then they show as *pending* in the preview.
- **Plain language (GenAI)** — write the rule the way you'd tell a colleague: *"only posts about open pedagogy; drop job ads and event announcements"*. aggRSSive's GenAI reads each item once and records its verdict, so a rule costs a fraction of a cent per new item and nothing afterwards. Available when the site has GenAI enabled — see [GenAI features](genai).

Both kinds work as *include* or *exclude*, and combine with keyword rules under the same any/all logic.

**Preview: included** shows what the rules currently let through and, for each item, *which rule* let it in; **Preview: kept out** shows recent items that didn't make it and why — *excluded by…*, *doesn't match…*, *duplicate*, *hidden by you*, or *pending* for items a meaning or plain-language rule hasn't analysed yet. Adjust rules and watch both lists change.

**Curation** — on any item:

- **pin** puts it at the top and lets it through regardless of rules
- **hide** removes it, even if rules would include it
- **note** adds a line of your own under it, shown wherever the bundle is published

**Settings** — title, description, public or private, match mode, an age window ("only items newer than 30 days"), the maximum number of items, and duplicate removal (the same link or title from two feeds appears once).

## Start from someone else's

On any public aggRSSive's page, **Copy to my aggRSSives** makes you a private copy with the same sources, rules and settings. Change it however you like; the original is untouched. It's how a curated list travels: someone builds it, others take it and adapt it.

## Public and private

Public aggRSSives appear on the *aggRSSives* page, can be embedded and subscribed to by anyone, and can be chosen by instructors inside an LMS. Private ones are yours alone: their embed code and feeds return nothing to anyone else.

## Rules on sources vs rules on bundles

A rule on a **source** applies everywhere that source is used — right for "this feed's *Comments on…* entries are never wanted". A rule on a **bundle** applies only there — right for "in *this* list, only the assessment posts".
