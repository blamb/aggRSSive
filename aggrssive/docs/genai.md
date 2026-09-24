---
title: GenAI features
order: 8
---

# GenAI features

aggRSSive can use a language model for the judgement calls that simple rules can't make: what a feed is about, which tags fit it, where it belongs in a classification. The features are **off** until a site admin adds an API key, and every one of them makes **proposals only** — a person accepts, edits or rejects each.

## What's available

- **Tag suggestions** — on a source page, **✨ ask aggRSSive (GenAI)** proposes three to six tags, preferring vocabulary already in use here so the collection stays consistent.
- **Classification suggestions** — the same button under *Classification* proposes Library of Congress and ISCED-F headings.
- **On add** — tick *Suggest tags and classification (GenAI)* when adding a feed and both run once after the first fetch, with the proposals waiting on the source page.

The free layer — suggested tags drawn from matching vocabulary and the feed's own categories — works with or without a key.

## Cost

Each click or on-add run is one short request, a fraction of a cent with the default model. A group adding a few hundred feeds a month spends well under a dollar. The site admin can set a spending cap on the provider's side.

## What is sent

The feed's title, description, site address, its current tags, and the titles of its most recent items — nothing about users, and nothing from private aggRSSives. Responses aren't stored beyond the proposals you see.

## Enabling it

A site admin adds an Anthropic API key as `ANTHROPIC_API_KEY` in the site's environment (see [Hosting](hosting)) and restarts the app. The ✨ buttons and the on-add checkbox appear as soon as the key is present; remove the key and they disappear.
