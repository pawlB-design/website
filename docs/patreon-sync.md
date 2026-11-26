# Patreon blog workflow

Source: https://www.patreon.com/c/Pawl_Boracchi — campaign `14367360`.
Adapted from TLF's importer; source content remains authoritative.

## Setup and commands

Only syncing needs Python (3.10+) and these dependencies:

```powershell
python -m pip install -r scripts/requirements.txt
python scripts/sync_patreon.py --all --discover-only
python scripts/sync_patreon.py --set-decision POST_ID mirror --reason "Reason for inclusion"
python scripts/sync_patreon.py --all
zola check --skip-external-links
zola build
```

Replace POST_ID with a discovered ID. `--set-decision` also accepts `skip` or
`review` and performs no network access. Read `scripts/patreon-inventory.json`
before imports; preserve decisions. New entries default to `review`. Select
additional posts when expanding the framework, rather than treating the initial
49-post discovery as an already completed mirror.

## Fidelity and safeguards

- Import only anonymously accessible, fully public posts from this campaign.
- Preserve original titles, wording, formatting, timestamps, captions and links.
- Keep one `content/blog/<initial-title>-<post-id>/index.md` per post. The manifest
  stores the stable slug and last imported file hash. Local edits stop updates.
- Images are local JPEGs under `static/images/blog/<post-id>/`, resized to fit
  1280px. Video and attachments remain linked on Patreon, not mirrored files.
- Unsupported structured formatting or legacy HTML fails for review. Do not
  silently replace it with a summary or bypass paid/private access.
- `skip` drafts an existing imported page after checking its hash; `review`
  pauses syncing but does not unpublish existing content. Removal from a live
  site requires a separate deployment that cleans stale files.
- A missing source post is reported, never automatically deleted.
- `scripts/patreon-manifest.json` tracks completed imports, not mere selections.
  `docs/patreon-posts.md` is generated from the inventory and local files.
- Read `.cache/patreon/sync-report.json` after every run. Resolve failures before
  reporting success. `--cached` reuses API JSON but may still download media.
- Patreon web endpoints are not a stable API. Inspect schema failures and access
  errors before changing extraction. No login/session credentials are needed.

The initial pilot is `132177380` (Welcome to Ømen Tide). No TLF posts, assets,
cached responses, manifest entries or editorial decisions were copied.
