# First-visit review: what a casual visitor can do, and where they stall

Walked on 2026-09-29 against the live site (signed out, desktop and phone width) and against a local copy of the same code as a fresh anonymous account. **Status (2026-09-29):** items 1, 2, 3 (noun: bundle), 4, 5, 6, 10, 11, 13, 15, 16 and the collapsing part of 9 are applied in commit ff973a2. Second batch (commit 1aedf14, amended): 7, 8, 12, 14 and the glossary. Still open: 9 (a further wording pass on the rule kinds, if wanted).

## What works today

**Signed out**, a visitor can: read the home page and the tag cloud; search Find feeds by subject and get feeds ranked by what they publish, plus the closest posts; browse any tag or classification heading and its latest items; open any source and its recent items; open any public aggRSSive, read it, use *related posts*, subscribe (RSS, Atom, JSON Feed, podcast app), copy any address, take the OPML; read all fourteen help pages. They cannot collect, add, tag or build anything, and the site does not tell them so until they look for a checkbox that is not there.

**With an anonymous account** (one tick, no email), they can additionally: add any feed, podcast (by name), platform page, watched page or bookmark; tag and classify; build an aggRSSive from the Heart-Cart, a tag, a heading or a search (topic); add rules; pin, hide, note; publish; export and import; get digests if mail is on. The only thing an anonymous account cannot do is place a list in a course, which needs an instructor inside the LMS, and any public list is already pickable there.

So the machine works. The problems are all in the first ten minutes: what things are called, what comes first on a page, and explanations that appear before the thing they explain.

## The list, most damaging first

### 1. The tip bar is the first thing on every page

On the home page the first element a visitor sees is a random tip about Zotero, above the headline; on a phone it fills the screen before "Collect. Tag. Filter." Same on Find feeds, sign-up and the help index. Tips are good; their position is wrong.

Change: render the tip bar after the page's `h1` (or after the hero on home), not above it; do not show tips on the sign-in, sign-up, anonymous and error pages; consider showing none on a visitor's first page view.

### 2. Signed-out visitors are told to tick boxes that do not exist

Find feeds opens with the key tip "Tick sources anywhere … they collect in the ♥ Heart-Cart", but signed-out pages have no checkboxes and no cart. Same on tag and heading pages.

Change: gate the checkboxes' key tip on `user`; for visitors show one line instead: "To collect feeds into a list of your own, sign in or try it without an account", with both links.

### 3. Two nouns for the same thing, and one of them is the site's name

The nav says **aggRSSives**; the page under it says "Bundles of sources"; the edit page says both; the help says "an aggRSSive: a live, filtered bundle". A newcomer cannot tell whether aggRSSive is the site, the list, or a verb. "Topic aggRSSive", "Copy to my aggRSSives", "Make an aggRSSive from these" compound it.

Change (a naming decision, yours): pick one everyday noun for the thing people make and use it in nav, headings and buttons; keep *aggRSSive* as the brand and, at most, as a nickname introduced once in Getting started. The cleanest is **list** ("Lists" in the nav, "Make a list from these", "Copy to my lists", "topic list"); "bundle" is the runner-up. Whichever it is, the word "bundle" then disappears from the interface.

### 4. Search results lead with what did not match

Searching *assessment* shows "Tags: No tags match. Classification headings: No headings match." at the top, and the real answer, ten feeds ranked by their posts and a dozen posts, below the fold. The visitor's first impression is failure.

Change: put *Feeds writing about this* first, then *Posts about this*, then tags and headings; hide any section with nothing in it instead of announcing it; show counts in the headings ("Feeds writing about this (10)").

### 5. The Heart-Cart is never introduced

It is named in tips and help, but on the page it is a hidden box that appears only after the first tick, in the bottom corner, with a heart. Nobody knows it is the way lists get made.

Change: when a signed-in person has ticked nothing, show the cart collapsed with one line: "Tick feeds anywhere and they collect here. Name them, and you have a list." Keep the name; explain it once where it lives.

### 6. Find feeds header is cluttered with export jargon

Beside the search box: "all 114 sources" in tiny text and "OPML of everything" with an icon, truncated at narrow widths. A newcomer does not know OPML, and it is not what they came for.

Change: move OPML links into a small "Take it with you" line at the bottom of the tag cloud and tree, and on the Sources page; leave the search row as search box, button, and "browse all 114 sources".

### 7. Codes without labels beside every feed

Result rows and source lists show tag chips followed by bare codes: "LB QA", "LC 0111". The label only appears on hover.

Change: in lists, show the heading's short label instead of the code ("Education theory", "Mathematics"), code on hover; keep codes on the classification pages themselves, where they are the point.

### 8. Odd tags surface in prominent places

The home tag cloud and Find page include *brilliant*, *jbm*, *ted*, *posthegemony*, *reclaim*; a public list called "brilliant" reads "Everything filed under brilliant." The starter collection's stance and credibility tags (*brilliant* looks like one) are not self-explaining outside that collection.

Change: rename credibility and stance tags with a visible prefix (*tier: brilliant* or *credibility: peer-reviewed*) or drop them from the cloud; retitle lists made from a tag as "Everything tagged brilliant". Consider hiding tags used by only one source from the home cloud.

### 9. The list edit page explains rules three times before you make one

In order: a key tip "How rules combine…", a second key tip on strictness, a muted line "Exclude rules always win…", the form, then a paragraph "Meaning rules compare each item…". Four explanations, a wall of text, and the form in the middle. *regex* is a checkbox label with no explanation; *strictness* is explained twice.

Change: one short line above the form ("Include lets things in; exclude always wins."), the strictness sentence as a tooltip on the strictness control, the meaning and plain-language paragraph collapsed under "What kinds of rule?", and "regex" labelled "regular expression".

### 10. The edit page's order puts suggestions before the list itself

A brand-new list opens as Sources → *Feeds like these* (seven suggestions led by arXiv with 127 similar posts) → Rules → Preview. The person has not yet seen what their list contains.

Change: Sources → Preview: included → Rules → Preview: kept out → Feeds like these → Settings.

### 11. "Anonymous OmA5" everywhere

The anonymous display name shows in the nav, on every list they publish ("by Anonymous OmA5"), and in the picker inside courses. It looks like a bug.

Change: ask for a display name on the anonymous page ("What should we call you? Optional"), default to plain "Anonymous" without the code; the code is already in the link.

### 12. The Add feed page teaches everything at once

Address box, a paragraph listing eight platforms, a key tip listing them again, podcast search with its own paragraph, a bookmark line, a tag-suggestion drawer. A person with one URL in hand has to read five things.

Change: one box that accepts either an address or a show's name and works out which (an address is anything with a dot and no spaces); the platform list becomes one collapsed "What can I paste?"; podcast search results appear under the same box.

### 13. Item lines repeat themselves

On list pages: "CogDogBlog · Sep 19, 2026 · CogDog The Blog": source title then the feed's author field, which for a one-person blog is the same name. Find results mix "May 26, 2026" and "11d ago" in one list.

Change: drop the author when it matches the source title (or when the source has a single author); pick one date style per page, relative within 30 days, dated beyond.

### 14. Source page suggestions are noisy and the glyphs are unexplained

Suggested tags for one blog: *abject, video, love-mongering, corporatization, higher education, blogging, tru, music*, each with ✓ ✎ ✕ and small links *refresh · accept all · reject all*. The suggestions come from the feed's own categories and are only as good as the feed's; ✎ means nothing until read about.

Change: cap heuristic suggestions at five, prefer vocabulary already in use here over the feed's own categories, give the three glyphs `title` text and a one-line legend on first use ("✓ add · ✎ edit first · ✕ not this"); move *accept all / reject all* to the end.

### 15. Sign-in and account entry points

"Try it without one" is on the home page only. From Find feeds or a list page, a visitor sees only "Sign in", which suggests they need an account already.

Change: nav for visitors reads "Sign in · Try it", with "Try it" going to the anonymous page.

### 16. Small things

- "Export all 0 of mine" on a fresh account; hide until there is one.
- The *File it* button (classification) and *Tag* button: fine for regulars; first-timers read "File it" as jargon. "Add heading" reads plainer.
- Help index has fourteen entries in one column with two long LMS titles; group as *Using it* / *In a course* / *Running the site*.
- The home stats line "114 sources · 4031 items · 4 aggRSSives" uses the site noun again; becomes "114 feeds · 4,031 posts · 4 lists" under item 3.
- "Sources" versus "feeds": the nav says Find feeds, the page says Sources, the count says sources. Pick *feeds* for people-facing text; *source* can stay in help for the bookmark/page cases.
- Phone width: the tag cloud's size differences are hard to see; the copy buttons are small targets; fine otherwise.

## A glossary would help, but only after the renaming

Getting started could carry a ten-line glossary (feed, list, tag, heading, rule, meaning rule, plain-language rule, topic list, bookmark list, Heart-Cart, embed). Writing it now would freeze the current names; do it after item 3.

## Suggested order

Items 1, 2, 4, 5, 6, 10, 11, 13 and 16 are small and independent of any naming decision; one commit. Item 3 is a decision, then a copy pass across nav, templates, tips and help. Items 7, 8, 9, 12, 14 and 15 follow.
