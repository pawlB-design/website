# Reference project map

Inspected 26 November 2026. Reference repositories were read only.

## Overdrive: C:\Projects\overdrive-website

| Source | Role | Pawl equivalent |
| --- | --- | --- |
| `config.toml` | Zola configuration, local base URL, extra settings | Same convention; Pawl metadata |
| `content/_index.md` | Homepage content | Same |
| `content/game/`, `content/lore/`, `content/models/` | Section indexes and individual Markdown entries | `content/games/` and `content/blog/` |
| `templates/` | Tera templates and reusable partials | Shared base, game grid, homepage, archive and article templates |
| `static/` | Directly served CSS, JS, fonts and images | CSS and imported blog media; no JS needed initially |
| `scripts/prepare-*.py` | Optional asset preparation | Not copied; Overdrive-specific art pipeline |
| `public/` | Generated static output | Same, ignored by Git |

Retained the self-contained Zola workflow, local base URL, direct CSS and
Markdown content. Did not copy the sci-fi frames, countdown, model catalogue,
newsletter, font assets or Overdrive copy.

## TLF: C:\Projects\tlf-website

| Source | Role | Pawl adaptation |
| --- | --- | --- |
| `content/blog/_index.md` | Date ordering, 24-post pagination, per-section feed | Same structure |
| `content/blog/<title>-<id>/index.md` | TOML metadata and original HTML body | Same structure |
| `templates/blog.html` | 3/2/1-column archive and pagination | Copied and adapted for Pawl |
| `templates/blog-post.html` | Title, date, source link, article | Simplified Pawl template |
| `templates/article-content.html`, `article-lightbox.html` | Shared media presentation and lightbox | Direct body rendering, responsive figures; no lightbox yet |
| `static/images/blog/<id>/` | Durable local media | Same convention |
| `scripts/sync_patreon.py` | Discovery, decisions, import, image conversion, hashes | Copied with Pawl campaign and user agent; Windows UTF-8 output fix |
| `scripts/article_index.py` | Metadata and local inventory helpers | Only the metadata reader is needed here |
| `scripts/patreon-inventory.json` | Source metadata and mirror/skip/review decisions | Fresh Pawl inventory |
| `scripts/patreon-manifest.json` | Completed imports, stable slugs, hashes | Fresh Pawl manifest |
| `docs/patreon-posts.md` | Readable generated inventory | Same convention |
| `.cache/patreon/` | Raw responses and sync reports | Same, ignored and never shipped |
| `scripts/build.py` | TLF-specific hidden-link cleanup and archive inventory | Not needed; direct `zola build` |

Front matter: `title`, `date`, `updated`; extra fields `patreon_id`,
`patreon_url`, `cover`. The manifest preserves the initial slug even when a
source title changes. Dates are original timestamps, not import dates.

The TLF mirror is selective, rather than literally every Patreon entry:
its inventory includes skipped posts retained locally as drafts. Pawl keeps
that distinction between discovery, editorial selection and completed imports.

## Pawl source verification

- Profile: https://www.patreon.com/c/Pawl_Boracchi
- Campaign `14367360`, verified via the anonymous welcome-post API response.
- Ømen Tide: https://www.patreon.com/Pawl_Boracchi/posts/welcome-to-omen-132177380
- Geste: https://www.patreon.com/Pawl_Boracchi/posts/geste-is-now-169905407

Initial discovery returned 49 entries. The welcome post is the small pilot;
the rest remain inventoried for review. Discovery alone does not establish full
public access. Consult the inventory and manifest for current completion state.
