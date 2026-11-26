# Pawl Boracchi

A small Zola site: homepage, games, and a Patreon-backed blog. No frontend build
chain, external fonts, analytics, database, or JavaScript dependency. This is a
local framework; the final identity, artwork, domain and hosting are still open.

## Preview and build

Requires Zola (verified with 0.22.1):

```powershell
zola serve --interface 127.0.0.1 --port 1111
zola check --skip-external-links
zola build
```

Visit http://127.0.0.1:1111. For production use
`zola build --base-url https://YOUR-DOMAIN.example`, then upload the contents of
`public/`. The configured loopback URL is a
development placeholder. Plain `zola check` also checks external services and
requires network access; Patreon may reject automated requests.

## GitHub Pages

`.github/workflows/pages.yml` builds and deploys on pushes to `main`, or manually
through **Actions → Build and deploy GitHub Pages → Run workflow** (select `main`).
It installs Zola 0.22.1, checks internal links, builds `public/`, uploads the Pages
artifact and deploys it using GitHub's built-in token. No custom secrets or
`gh-pages` branch are required. Patreon sync is a separate local operation;
commit imported Markdown and media before pushing.

On your end, set **Settings → Pages → Build and deployment → Source** to
**GitHub Actions**. The workflow reads the configured Pages URL automatically,
including a repository prefix or custom domain. With the current remote and no
custom domain, the expected URL is `https://pawlb-design.github.io/website/`.
Only `main` can deploy; the `github-pages` environment must allow that branch.

To check the repository-prefix build locally without changing the running preview:

```powershell
zola build --base-url https://pawlb-design.github.io/website --output-dir .cache/pages-check
```

Blog images are resolved against that base URL in both article pages and RSS;
the original imported files and their sync hashes remain unchanged.
Workflow setup follows [GitHub's custom Pages workflow documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

## Editing

- `config.toml`: site metadata and Patreon profile.
- `content/_index.md`: introduction.
- `content/games/`: game descriptions and ordering.
- `content/blog/<slug>-<post-id>/index.md`: mirrored posts.
- `templates/`: shared layout, page types and archive.
- `static/site.css`: responsive styles; system fonts and a simple dark palette.
- `static/images/blog/<post-id>/`: imported media, when present.

The blog uses 24 posts per page, newest first, with RSS at `/blog/rss.xml`.
Post bodies retain original source wording; the brief game descriptions and
homepage copy are starter copy, not quotes or a final brand direction.

See [the reference-project map](docs/structure-map.md),
[Patreon workflow](docs/patreon-sync.md), and
[discovered post inventory](docs/patreon-posts.md).
