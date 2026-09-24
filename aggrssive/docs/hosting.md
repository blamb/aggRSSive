---
title: Hosting
order: 10
---

# Hosting aggRSSive

aggRSSive is a single container with one data volume. It runs anywhere Docker does; Reclaim Cloud is the reference setup.

## Reclaim Cloud, step by step

Every push to the project's `main` branch publishes a container image at `ghcr.io/blamb/aggrssive:latest`.

1. **New Environment → Custom** (Docker). *Select Image → Custom → Add New Image*, name `ghcr.io/blamb/aggrssive`, tag `latest`.
2. **Variables** (the layer's gear → *Variables*):
   - `SECRET_KEY` — a long random string
   - `BASE_URL` — `https://<environment>.<region>.reclaim.cloud`
   - `JELASTIC_EXPOSE` — `8000`
   - optionally `ANTHROPIC_API_KEY` for [GenAI features](genai)
3. Turn on **Built-In SSL**; leave *Public IPv4* off. The `/data` volume is created automatically.
4. Name the environment and **Create**. The first visit to the site creates the first (full admin) account.

**Updating**: after a new image is published, the layer's **Redeploy Containers** action with tag `latest`. The volume, and so the database, is kept. A redeploy takes about two minutes; changing a variable is a fifteen-second restart.

**Backups**: the whole site is the file `/data/aggrssive.db` plus `/data/lti_private_key.pem`. Copy them. (`/data/models` holds the downloaded embedding model and can always be re-fetched.)

**Meaning rules** download a small embedding model (about 64 MB) into `/data/models` the first time they're needed, and hold roughly 300 MB of memory while analysing. Set `EMBEDDINGS_ENABLED=false` in the variables to switch the feature off on a very small container.

## Same-cloud LMS

If your Moodle (or other LMS) is on the same Reclaim account, add `DNS_OVERRIDES=<lms-host>=http://<lms node's private IP>` to the variables. Inside the platform, sibling environments resolve to private addresses without HTTPS, and the public load balancer isn't reachable, so this routes aggRSSive's calls over the private network. Find the private IP in the LMS node's `MASTER_IP` variable. The reverse direction needs the LMS to hold aggRSSive's public key directly — see [the LTI admin guide](lti-admin).

## Anywhere else

```
docker run -d -p 8000:8000 -v aggrssive-data:/data \
  -e SECRET_KEY=… -e BASE_URL=https://your.host ghcr.io/blamb/aggrssive:latest
```

Put it behind any HTTPS reverse proxy. All settings are environment variables; `.env.example` in the source lists them.
