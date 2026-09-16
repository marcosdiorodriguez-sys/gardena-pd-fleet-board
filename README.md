# Gardena PD Fleet Service Board

Live, read-only overdue / due-soon / scheduled-this-week maintenance board for
the Gardena PD fleet, serviced by Shige's Premier Auto Service. Built because
Whip Around's own dashboard has stale/incomplete data and isn't synced to
Tekmetric.

**Live URL:** set once GitHub Pages is enabled on this repo (Settings → Pages
→ Source: GitHub Actions). It will be:
`https://<your-github-username>.github.io/<this-repo-name>/`

## How this site updates

This is a fully static page — `index.html` is the whole site, with its data
baked directly into a `const FLEET = [...]` block in the page's own
`<script>`. There is no backend and no build step.

An hourly automated job (a Claude scheduled task, running on Alex's
computer) pulls fresh data from Whip Around, recomputes each vehicle's
status, and pushes an updated `index.html` to this repo's default branch.
GitHub Pages (via the included Actions workflow) redeploys automatically on
every push — usually live within a minute or two.

See `phase4-refresh-runbook.md` in the main WhipAround project folder for
the exact refresh procedure, and `PROJECT.md` there for full project history
and decisions.

## Manual local preview

Just open `index.html` directly in a browser — no server needed.
