---
title: "Moodle and other LMSs: for admins"
order: 8
---

# Connecting aggRSSive to a learning platform

aggRSSive is an **LTI 1.3 Advantage** tool with Deep Linking. Register it once per platform; instructors then add any public aggRSSive to their courses with the platform's content picker. Registration is done by a site admin at **Admin → LTI platforms**.

## Moodle (dynamic registration)

1. In Moodle: *Site administration → Plugins → Activity modules → External tool → Manage tools*.
2. Paste the **dynamic registration URL** from *Admin → LTI platforms* into *Tool URL* and click **Add LTI Advantage**.
3. A window opens, aggRSSive registers itself, and the window closes. If the new tool card says *Pending*, click **Activate**.
4. Open the tool's settings (pencil icon) and check that *Supports Deep Linking* is on and *Tool configuration usage* is *Show in activity chooser and as a preconfigured tool*.

That's normally all. The platform appears in the list on *Admin → LTI platforms*, and its *last launch* time updates as people use it.

## Other platforms (manual registration)

Platforms without dynamic registration ask for a handful of URLs, all listed on *Admin → LTI platforms*:

| They ask for | Give them |
|---|---|
| Tool / target link URL, redirect URI, deep linking URL | `…/lti/launch` |
| Initiate login URL | `…/lti/login` |
| Public keyset / JWKS URL | `…/lti/jwks.json` |
| Public key (if they want the key itself) | shown on the page |

They give you back a *client ID*, *platform ID (issuer)*, an *authentication URL*, an *access token URL*, a *public keyset URL* and a *deployment ID*. Paste those into **Add platform manually** on the same page.

## When both sites live on the same cloud

If aggRSSive and the platform are hosted on the same Jelastic-based cloud (Reclaim Cloud, for instance), the two may fail to reach each other by name: each resolves the other to a private address that doesn't serve HTTPS. Two adjustments fix it, and are documented in the hosting guide:

- On aggRSSive, set `DNS_OVERRIDES` so it reaches the platform over the private network — see [Hosting](hosting).
- On the platform, give it aggRSSive's public key directly instead of the keyset URL (in Moodle: tool settings → *Public key type: RSA key*, paste the key from *Admin → LTI platforms*).

## Settings for each platform

Platforms differ, so anything that depends on the platform is a setting rather than a rule in the code. Under each registered platform on *Admin → LTI platforms*, open **Settings for this platform**:

| Setting | Default | When to change it |
|---|---|---|
| Show *related posts* under items | on | Turn off for a plain list, or if the platform's frame is narrow |
| Open item links in a new tab | on | Turn off if the platform prefers navigation inside its frame |
| Carry the Deep Linking response in the return URL | on | Moodle needs it after a login round-trip; turn off if a platform rejects long URLs |
| Frame height asked for | 600 px | Platforms that honour the request get a taller or shorter list |
| Default items per launch, default descriptions | 10, short excerpt | Pre-filled in the instructor's picker; also used when a resource link was added by URL and says nothing |

Changes apply to the next launch; nothing already placed in a course needs re-adding.

## Privacy

aggRSSive receives from the platform a user identifier, name and email (when the platform shares them) and the user's role. It uses the role to decide whether to show the *edit* link, and stores nothing about individual users. Launches don't require an aggRSSive account.

## Removing a platform

*Admin → LTI platforms → remove*. Existing activities in that platform's courses stop working immediately.
