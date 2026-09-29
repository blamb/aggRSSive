---
title: GenAI features
order: 10
---

# GenAI features

aggRSSive can use a language model for the judgement calls simple rules can't make: what a feed is about, which tags fit it, where it belongs in a classification. The features are **off** until a site admin adds an API key, and every one of them only **proposes**. A person accepts, edits or rejects each.

## What's available

- **Tag suggestions** — on a source page, **✨ ask aggRSSive (GenAI)** proposes three to six tags, preferring vocabulary already in use here so the collection stays consistent.
- **Classification suggestions** — the same button under *Classification* proposes Library of Congress and ISCED-F headings.
- **On add** — tick *Suggest tags and classification (GenAI)* when adding a feed and both run once after the first fetch, with the proposals waiting on the source page.
- **Plain-language rules** — in a bundle's or source's rules, choose the field *plain language (GenAI)* and describe what you want kept: *"only items about assessment design; drop job postings"*. Each new item is judged once and the verdict kept, so the rule keeps working at no further cost. Judging happens in the background within a few minutes of a fetch, and for a small batch immediately when someone views the bundle. See [Building a bundle](bundles).

*Meaning* rules, the meaning search on *Find feeds*, *related posts* and *feeds like these* are different: they use a small model that runs locally on the server, need no key, send nothing anywhere, and cost nothing per item.

The free layer — suggested tags drawn from matching vocabulary and the feed's own categories — works with or without a key.

## Cost

Each click or on-add run is one short request, a fraction of a cent with the default model. Plain-language rules cost about the same per new item per rule, in batches of twenty-five. A group adding a few hundred feeds a month and running a handful of such rules spends a dollar or two. The site admin can set a spending cap on the provider's side.

## What is sent

For tag and classification proposals: the feed's title, description, site address, its current tags, and the titles of its most recent items. For plain-language rules: the rule's text and, for each item judged, its title and a short excerpt. Nothing about users, nothing from private bundles, and never the personal note on a bookmark. See [Privacy](privacy). Responses aren't stored beyond the proposals you see and the yes/no verdicts a rule keeps.

## Enabling it

A site admin adds an Anthropic API key as `ANTHROPIC_API_KEY` in the site's environment (see [Hosting](hosting)) and restarts the app. The ✨ buttons and the on-add checkbox appear as soon as the key is present; remove the key and they disappear.
