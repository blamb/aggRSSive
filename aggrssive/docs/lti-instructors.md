---
title: "Moodle and other LMSs: for instructors"
order: 7
---

# Adding an aggRSSive to a course

Once an admin has connected aggRSSive to your platform (see [the admin guide](lti-admin)), adding a list to a course takes a minute and needs no account on aggRSSive.

## In Moodle

1. In your course, turn **Edit mode** on and click **Add an activity or resource**.
2. Choose **External tool**, then pick **aggRSSive** as the preconfigured tool. (On some sites the tool appears directly in the activity chooser under its own name.)
3. Click **Select content**. A picker opens listing every public aggRSSive. Search, choose one, and set how many items to show and whether to include descriptions and images.
4. Click **Add to course**, then **Save and return to course**.

The activity shows the live list. As the feeds update, so does the page. Students see the list only; instructors also get an **edit in aggRSSive** link.

## In Canvas, Brightspace, Blackboard and others

The same flow under different names: add an *External tool* / *LTI app* item, choose aggRSSive, and use its content picker. Deep Linking (the picker) is part of the LTI 1.3 standard, so any platform that supports it works the same way. If your platform only offers a plain launch without a picker, ask your admin for a launch URL of the form `…/lti/launch?bundle=abcd1234` — the code is on the aggRSSive's page.

## Changing what's shown

The list is the aggRSSive itself, so change it in aggRSSive: add or remove sources, adjust rules, pin or hide items. The course updates on the next page load. To show a different aggRSSive, edit the activity and use *Select content* again.

Under each item, *related posts* opens the closest posts from the whole collection. Links open in a new tab so students don't lose their place in the course. Your aggRSSive administrator can change both for the platform.

## Troubleshooting

- **"This aggRSSive no longer exists or has been made private"** — its owner made it private or deleted it. Choose another.
- **"Launch state is missing or was already used"** — the page was reloaded mid-launch. Go back to the course and open the activity again.
- **A blank frame** — some browsers block third-party content in frames. aggRSSive is built not to need cookies inside the frame, so this is usually the platform's own frame settings; opening the activity in a new window works.
