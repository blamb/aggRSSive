# aggRSSive — working notes for contributors (human or AI)

## Non-negotiables

- **Docs move with code.** Any change to what a person sees or does updates the matching page in `aggrssive/docs/` in the same commit. The Help section (`/help`) renders those files; there is no other user documentation.
- **LTI interoperability.** Anything an instructor or student sees must work through a standard LTI 1.3 launch on any platform, not just Moodle. Platform quirks become per-platform settings, never assumptions in the code.
- **Proposals, not actions.** GenAI features propose; a person accepts, edits or rejects. Nothing is applied automatically.
- **One container, one volume.** Keep SQLite and the in-process scheduler unless there's a concrete reason. New files the app needs at runtime go under `aggrssive/` and must be listed in `[tool.setuptools.package-data]` — and never under a path that `.gitignore` swallows (`/data/` is the local database folder; `aggrssive/data/` is shipped framework data).

## Conventions

- Tests: `.venv/bin/pytest`. Add a test for behaviour, not for wiring.
- Deployment: push to `main` builds and smoke-tests the image, then publishes to GHCR; a Reclaim Cloud *Redeploy* pulls it. Batch changes; each redeploy is ~2 minutes of downtime.
- Base image is pinned to Debian 12 because Reclaim rejects newer ones.
- The "ask aggRSSive (GenAI)" wording is deliberate; don't rename it to the model's name.
- Roles: `user` / `site_admin` / `admin` (see `docs/roles.md`). Permission checks live in `auth.py`.
