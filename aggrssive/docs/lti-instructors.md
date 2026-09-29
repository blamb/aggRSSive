---
title: "Moodle and other LMSs: for instructors"
order: 8
---

# aggRSSive inside a course

Once an admin has connected aggRSSive to your platform (see [the admin guide](lti-admin)), you can add live lists to a course, change them, and make new ones, without leaving the course for more than a tab. Nothing is copied into the LMS: the course shows the aggRSSive as it is now, and as it changes.

## Add a list to a course

In **Moodle**:

1. Turn **Edit mode** on and click **Add an activity or resource**.
2. Choose **External tool**, then **aggRSSive** as the preconfigured tool. (On some sites it sits directly in the activity chooser under its own name.)
3. Click **Select content**. A picker opens listing every public aggRSSive, with yours first. Search, choose one, and set how many items to show and whether to include descriptions and images. The starting values are your platform's defaults.
4. Click **Add to course**, then **Save and return to course**.

In **Canvas, Brightspace, Blackboard and others** the flow is the same under different names: add an *External tool* or *LTI app* item, choose aggRSSive, use its content picker. The picker (Deep Linking) is part of the LTI 1.3 standard. If your platform only offers a plain launch with no picker, ask your admin for a launch address of the form `…/lti/launch?bundle=abcd1234`; the code is on the aggRSSive's page.

## What students see

The live list: title, source, date, a short excerpt or the full text, images if you chose them. Under each item, **related posts** opens the closest posts from the whole collection. Longer lists get a **filter box** to narrow by a word. Podcast episodes get a **player** and the footer offers the list's RSS for a podcast app. Links open in a new tab so nobody loses their place in the course. Students need no aggRSSive account and none is created for them.

## What you can do from the course

You have an aggRSSive account without signing up for one: the first time you open aggRSSive from a course, an account tied to your LMS identity is created, and the links below open aggRSSive already signed in as you.

- **Edit in aggRSSive**, in the activity's header, opens the list's edit page in a new tab: add or remove sources, add rules (keywords, a meaning, or plain language), pin the items that matter, hide the ones that don't, write a note under an item. The course shows the change on its next load. If the list is someone else's, the link opens its page instead, where **Copy to my aggRSSives** gives you your own version to edit and place.
- **Make a new aggRSSive**, at the bottom of the picker, opens *Find feeds* signed in. Tick sources into the Heart-Cart, name the aggRSSive, mark it public on its edit page, then return to the picker and choose it. A tag page or a classification heading can be turned into an aggRSSive in one click; a page with no feed can be watched; single pages go in a bookmark list.
- **Rules work on episodes and posts alike**, so a podcast bundle can keep only the interviews, or a news bundle only the items mentioning your topic.
- **Email digests**: on any aggRSSive's page, signed in, choose daily or weekly and new items come to your address.
- **Reuse elsewhere**: the same aggRSSive has embed code for any web page or WordPress site, and an export file for another aggRSSive install. Placing it in a second course is *Select content* again.

To use aggRSSive outside the course with a password, open your name → Account and set one; your LMS launches keep working either way.

## Changing what's shown

The list is the aggRSSive itself, so change it in aggRSSive: sources, rules, pins, hides, notes. To show a different aggRSSive, edit the activity and use *Select content* again. To change how many items or whether descriptions show, do the same; the picker remembers nothing, so re-enter the options.

## Troubleshooting

- **"This aggRSSive no longer exists or has been made private"**: its owner made it private or deleted it. Choose another, or ask them to make it public again.
- **"Launch state is missing or was already used"**: the page was reloaded mid-launch. Go back to the course and open the activity again.
- **"That link has expired"** after clicking *edit*: the signed-in link lasts an hour. Open the activity again and click it afresh.
- **A blank frame**: some browsers block third-party content in frames. aggRSSive needs no cookies inside the frame, so this is usually the platform's own frame settings; opening the activity in a new window works.
