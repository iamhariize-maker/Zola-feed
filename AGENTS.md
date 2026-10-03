# AGENTS.md: working on the Zola feed

This repo is the live data feed for the Zola Corpus app (https://iamhariize-maker.github.io/zola-corpus/, code in
`iamhariize-maker/zola-corpus`, which has its own `AGENTS.md` and `docs/ROADMAP.md`). The app reads one file:

    https://raw.githubusercontent.com/iamhariize-maker/zola-feed/main/zola-feed.json

## Files

| File | Job |
|---|---|
| `zola-feed.json` | The feed. Schema `zola-feed/1`. Hand-edited, except `inbox`, which the bot writes |
| `scripts/update_feed.py` | Fetches RSS (`SOURCES`), tags headlines (`SUBJECTS`, `MACHINES`), keeps only relevant ones, validates, writes |
| `scripts/eval_tags.py` | Prints KEEP or drop and the tags for real headlines. Run it before and after any keyword change |
| `.github/workflows/update-feed.yml` | Every 6 h and on demand: validate, refresh inbox, commit. On push or PR: validate only |

## Rules

- **Never break the schema.** `python scripts/update_feed.py --check` must pass before any push. The workflow runs
  it on every push and PR, and the app refuses a malformed file (it keeps its last good copy).
- **Bump `updated`** (ISO time, UTC) on every hand edit. The app ignores a file older than the one it has.
- Exactly one exam may have `"primary": true`; it drives "days to Prelims" and the calendar export.
- Links must be `https://`. Text is shown as text, never run as code.
- `subjects` must stay within the app's chips: `Polity`, `Economy`, `Environment`, `S&T`, `IR`, `History`.
  Machines are `M01` to `M23` (see `MACHINES`).
- Tags are hints and the app labels them so. Prefer missing a tag to a wrong one. A bare word that is
  ambiguous ("President", "delegation") needs context in the pattern.
- The bot commits as `zola-feed-bot`. If it loses a race with a hand edit it resets to the new `main` and re-runs,
  so hand edits are never overwritten. Do not change that loop without keeping that property.

## Commands

```bash
python scripts/update_feed.py --check   # validate zola-feed.json
python scripts/eval_tags.py             # review tagging on real headlines (needs network)
python scripts/update_feed.py           # refresh the inbox locally (normally the bot does this)
```

Python 3.10+ with no dependencies. GitHub Actions: Actions tab → "Update Zola feed" → Run workflow.

## Status and next steps

- Done: English PIB source (`Reg=3`), first-seen dates (PIB has none), stricter validation, race-safe bot,
  relevance filter (only tagged releases reach the inbox) and wider keyword lists (17 of 20 kept on 3 Oct 2026,
  up from 3).
- Next (see `zola-corpus/docs/ROADMAP.md`, item 4): build a 200-headline evaluation set with expected tags,
  get correct tags on 80% or more of kept items with under 15% false keeps, and improve `M01`–`M23` matching. Possibly
  add PRS legislative briefs or regional PIB feeds to `SOURCES`.
- Exam dates: add APSC dates to `exams` when the APSC calendar is published.
