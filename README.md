# Zola feed

This repository is the live feed for Zola Corpus 2.4. The app reads one file from it,
`zola-feed.json`, whenever you open the app with an internet connection. Without a
connection the app uses its built-in data, or the last copy of this file it saved.

## Set it up once

The files are already here. What is left is two clicks on GitHub:

1. Open the **Actions** tab and allow workflows if GitHub asks. Then open
   **Update Zola feed** and press **Run workflow** once. The inbox fills within a minute.
2. The app at https://iamhariize-maker.github.io/zola-corpus/ is already pointed at
   `https://raw.githubusercontent.com/iamhariize-maker/zola-feed/main/zola-feed.json`
   (GitHub addresses ignore upper/lower case, so `Zola-feed` and `zola-feed` are the same repo).
   Open it, tap **Go live** in the header and press **Check now**. The dot turns green.
   If you rename this repo, paste the new Raw address there and press **Save and check**.

The feed must be on the `main` branch and the repository must stay **public**; the app reads the raw file.

## What updates by itself

- **News inbox.** Every six hours the workflow reads the RSS sources listed at the top of
  `scripts/update_feed.py` (PIB, English, all ministries by default) and adds new releases.
  PIB's feed carries no dates, so each release is dated when the bot first sees it (within six hours)
  and dropped after 45 days. Each release is matched to
  machines and subjects by keywords. These matches are hints, not verified links, and the app
  labels them that way. If a source stops answering, the inbox simply stops growing; nothing breaks.
  If PIB ever changes its RSS address, open it in a browser, copy the new address and replace it
  in `SOURCES`.

## What you (or Claude, in a later session) edit by hand

Edit `zola-feed.json` on GitHub (pencil icon). The workflow checks every edit and fails loudly if
the file is malformed (bad dates, a second primary exam, duplicate ids, unknown notice levels or
statuses, links that are not `https://`), and the app refuses a malformed file and keeps its saved copy.
Your edits are safe from the bot: if it was mid-run when you saved, it starts again from your version.

- `exams`: dates and the countdown. Exactly one entry may have `"primary": true`; that date drives
  "days to Prelims". Add APSC dates here when the APSC calendar is out.
- `watch`: extra dates for the Forecast watch list (`date`, `title`, `hook`, `kind`).
- `events`: curated current-affairs items (`id`, `date`, `title`, `subject`, `hook`,
  `status` = `UNVERIFIED` or `VERIFIED`, `machines` such as `["M14"]`, `source` with `title` and `url`).
- `notices`: short corrections or warnings shown under the header (`level`: `info`,
  `correction` or `warning`; only corrections and warnings are shown).
- `edition`: set `latest` to a newer edition number and `url` to where it can be downloaded.

Always bump `updated` when you edit; the app ignores a file older than the one it already has.

## Privacy and safety

The app sends one plain request for this file. No account, cookies or tracking. Every field is
validated, length-capped and shown as text; links must be `https://`; nothing in the file is ever
run as code. The feed can never change the verified rules inside the machines.
