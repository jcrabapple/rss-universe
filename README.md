# The RSS Universe

A living directory of RSS readers, feed generators, monitoring tools, directories, and standards — every link verified live before it was added.

Live at: **https://toolbox.rss.here.now/**

## What's inside

A single self-contained `index.html` — no build step, no dependencies, no external assets. Warm cream-and-orange editorial theme with a dark mode toggle (preference persisted in `localStorage`).

- **80 apps & tools** across 12 categories: web/hosted readers, self-hosted readers, desktop & mobile readers, podcast readers, feed generation, monitoring & alerts, search & discovery, standards & formats, dev libraries, browser extensions, curated lists, and read-it-later
- All external links open in new tabs
- Every candidate link was HTTP-checked during research; dead links were dropped or corrected before publishing

## Deploying

The site is published to here.now (a workspace under the `rss` subdomain, label `toolbox`). To republish after edits, use the here.now publish flow (the `here-now` skill has the full workspace procedure):

```bash
# publish.sh doesn't support workspace targeting — use the direct API flow
# create/update with X-HereNow-Account header, upload, finalize
```

Local working copy lives in this repo; the live deployment is updated from `index.html`.
