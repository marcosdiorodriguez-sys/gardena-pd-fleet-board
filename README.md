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

An hourly GitHub Actions workflow pulls fresh data from Whip Around, recomputes
each vehicle's status, and commits an updated `index.html` to the default
branch. GitHub Pages redeploys automatically on every push, so no personal
computer needs to be on.

## One-time GitHub setup

In this repository, go to **Settings → Secrets and variables → Actions** and
create a repository secret named `WHIPAROUND_API_KEY` containing the Gardena PD
Whip Around API key. Never put the key in a file, commit, workflow input, or
Actions variable. Then open **Actions → Refresh fleet data** and run the
workflow once to verify the key and Whip Around connectivity.

The workflow needs permission to push its refreshed `index.html`. Under
**Settings → Actions → General → Workflow permissions**, select **Read and write
permissions** if the repository's current policy does not already permit it.
If `main` has branch protection, allow GitHub Actions to push or exempt this
workflow's bot commits.

The schedule is hourly at minute 17. GitHub may start scheduled workflows a few
minutes late during busy periods. A failed fetch exits before changing the page,
leaving the prior good data and its visible "last pulled" timestamp in place.

The implementation is in `scripts/refresh_board.py`; its status calculations
preserve the existing 500-mile / 14-day due-soon window and 7-day scheduled
section. The older device-bound runbook in the parent Fleet Management project
is no longer needed after this workflow succeeds.

## Manual local preview

Just open `index.html` directly in a browser — no server needed.
