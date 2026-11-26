"""Sync approved public Patreon posts. Default: latest 10; --all walks the archive.

Only anonymous, fully readable posts are imported. Unknown formatting fails
closed. Existing files are updated only if their previous import hash matches.
"""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
from html import escape
from io import BytesIO
import json
from pathlib import Path
import re
import sys
import time
from urllib.parse import urlencode, urlsplit
from urllib.request import urlopen, Request

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / '.cache/patreon'
MANIFEST = ROOT / 'scripts/patreon-manifest.json'
CAMPAIGN = '14367360'
INVENTORY = ROOT / 'scripts/patreon-inventory.json'
INVENTORY_VIEW = ROOT / 'docs/patreon-posts.md'


def save_inventory(inventory, manifest):
    INVENTORY.write_text(json.dumps(inventory, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
    rows = ['# Patreon post inventory', '',
            'Generated from `scripts/patreon-inventory.json`. Decisions persist by Patreon ID.',
            'Use the sync script to change decisions; do not edit this generated table.', '',
            '| Date | Post | Decision | Website state | Reason |',
            '| --- | --- | --- | --- | --- |']
    def cell(value):
        return str(value or '').replace('|', '\\|').replace('\n', ' ')
    for pid, entry in sorted(inventory['posts'].items(), key=lambda item: item[1].get('published_at') or '', reverse=True):
        old = manifest['posts'].get(pid)
        state = 'Not mirrored'
        if old:
            source = ROOT / 'content/blog' / old['slug'] / 'index.md'
            if not source.exists():
                state = 'Source file missing'
            else:
                from article_index import metadata
                state = 'Excluded (draft)' if metadata(source).get('draft') else 'Mirrored locally'
            state = '[' + state + '](../content/blog/' + old['slug'] + '/index.md)'
        if entry.get('last_error'):
            state += '; sync error: ' + cell(entry['last_error'])
        rows.append('| ' + ' | '.join([cell(entry.get('published_at', '')[:10]), '[' + cell(entry['title']) + '](' + entry['url'] + ')', entry['decision'], state, cell(entry.get('reason'))]) + ' |')
    INVENTORY_VIEW.write_text('\n'.join(rows) + '\n', encoding='utf8')


def remember_post(inventory, post, manifest):
    pid, a = post['id'], post['attributes']
    entry = inventory['posts'].setdefault(pid, {
        'decision': 'mirror' if pid in manifest['posts'] else 'review',
        'reason': 'Already imported in the initial batch.' if pid in manifest['posts'] else '',
    })
    entry.update(title=a['title'], url=a['url'], published_at=a.get('published_at'),
                 edited_at=a.get('edited_at'))
    return entry


def set_decision(inventory, manifest, pid, decision, reason):
    entry = inventory['posts'][pid]
    old = manifest['posts'].get(pid)
    if old and decision == 'skip':
        dest = ROOT / 'content/blog' / old['slug'] / 'index.md'
        text = dest.read_text(encoding='utf8')
        if digest(text) != old['file_hash']:
            raise ValueError('Local edits detected; reconcile before excluding this article')
        marker = 'draft = true # Excluded by Patreon inventory\n'
        if marker not in text:
            text = text.replace('+++\n', '+++\n' + marker, 1)
            dest.write_text(text, encoding='utf8')
            old['file_hash'] = digest(text)
            MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
    entry.update(decision=decision, reason=reason, decided_at=datetime.now(timezone.utc).isoformat())


def fetch(url):
    if urlsplit(url).scheme != 'https':
        raise ValueError('Expected HTTPS URL')
    with urlopen(Request(url, headers={'User-Agent': 'PawlBoracchi-Website-Mirror/1.0'}), timeout=60) as r:
        return r.read()


def digest(text):
    return sha256(text.encode('utf-8')).hexdigest()


def safe_link(url):
    if urlsplit(url).scheme not in ('https', 'http', 'mailto'):
        raise ValueError('Unsupported link: ' + url)
    return escape(url, quote=True)


class Renderer:
    def __init__(self, post, media):
        self.post = post
        self.media = media
        self.images = {}
        self.warnings = []
        self.url = post['attributes']['url']

    def image(self, url, key, alt='', caption=''):
        if not url:
            raise ValueError('Missing image URL')
        key = re.sub(r'[^a-zA-Z0-9_-]', '-', str(key))
        path = '/images/blog/' + self.post['id'] + '/' + key + '.jpg'
        # Download each image once per run; stable names avoid signed-URL churn.
        if path not in self.images:
            raw = fetch(url)
            with Image.open(BytesIO(raw)) as im:
                im = ImageOps.exif_transpose(im).convert('RGB')
                im.thumbnail((1280, 1280))
                output = BytesIO()
                im.save(output, format='JPEG', quality=85, progressive=True)
                self.images[path] = output.getvalue()
        return '<figure><img src="' + path + '" alt="' + escape(alt, quote=True) + '" loading="lazy">' + ('<figcaption>' + escape(caption) + '</figcaption>' if caption else '') + '</figure>\n'

    def video(self):
        self.warnings.append('Video retained as a link to the Patreon post (expiring playback URL).')
        return '<p class="blog-media-note"><a href="' + safe_link(self.url) + '">Watch this video on Patreon</a></p>\n'

    def node(self, n):
        kind = n['type']
        attrs = n.get('attrs') or {}
        inner = ''.join(self.node(c) for c in n.get('content', []))
        if kind == 'text':
            inner = escape(n['text'])
            for m in n.get('marks', []):
                mark = m['type']
                tags = {'bold': 'strong', 'italic': 'em', 'strike': 's', 'underline': 'u', 'code': 'code'}
                if mark == 'link':
                    inner = '<a href="' + safe_link(m['attrs']['href']) + '">' + inner + '</a>'
                elif mark in tags:
                    tag = tags[mark]
                    inner = f'<{tag}>{inner}</{tag}>'
                else:
                    raise ValueError('Unknown text mark: ' + mark)
            return inner
        if kind == 'doc':
            return inner
        if kind == 'image':
            return self.image(attrs['src'], attrs.get('media_id') or digest(attrs['src'].split('?')[0])[:12], attrs.get('alt') or '', attrs.get('caption') or '')
        if kind == 'video':
            return self.video()
        if kind == 'hardBreak':
            return '<br>'
        if kind == 'horizontalRule':
            return '<hr>\n'
        tags = {'paragraph': 'p', 'blockquote': 'blockquote', 'bulletList': 'ul', 'orderedList': 'ol', 'listItem': 'li', 'codeBlock': 'pre'}
        if kind == 'heading':
            tag = 'h' + str(min(6, max(2, int(attrs.get('level', 2)) + 1)))
        elif kind in tags:
            tag = tags[kind]
        else:
            raise ValueError('Unknown content node: ' + kind)
        extra = ' start="' + str(int(attrs['start'])) + '"' if kind == 'orderedList' and attrs.get('start') else ''
        return f'<{tag}{extra}>{inner}</{tag}>\n'

    def render(self):
        a = self.post['attributes']
        if not a.get('current_user_can_view') or a.get('is_paid') or not a.get('published_at'):
            raise ValueError('Not a verified public published post')
        campaign = self.post.get('relationships', {}).get('campaign', {}).get('data', {}).get('id')
        if campaign != CAMPAIGN:
            raise ValueError('Wrong campaign')
        if not a.get('content_json_string'):
            raise ValueError('Structured full text unavailable; review legacy HTML before importing')
        body = self.node(json.loads(a['content_json_string']))
        gallery = ''
        order = (a.get('post_metadata') or {}).get('image_order') or [x['id'] for x in self.post.get('relationships', {}).get('images', {}).get('data', [])]
        for mid in order:
            m = self.media[mid]['attributes']
            urls = m.get('image_urls') or {}
            url = urls.get('original') or urls.get('default') or m.get('download_url')
            gallery += self.image(url, mid)
        if a['post_type'].startswith(('video', 'audio')):
            gallery += self.video()
        if self.post.get('relationships', {}).get('attachments_media', {}).get('data'):
            self.warnings.append('Attachments remain on Patreon.')
            body += '<p><a href="' + safe_link(self.url) + '">Download the attachments on Patreon</a></p>\n'
        return gallery + body


def main():
    # Windows redirected consoles may default to a legacy encoding.
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--cached', action='store_true', help='Use the saved latest batch; still downloads images')
    parser.add_argument('--discover-only', action='store_true', help='Refresh metadata inventory without importing posts or images')
    parser.add_argument('--set-decision', nargs=2, metavar=('POST_ID', 'DECISION'), help='Set mirror, skip, or review; no network access')
    parser.add_argument('--reason', default='')
    args = parser.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text(encoding='utf8')) if MANIFEST.exists() else {'campaign_id': CAMPAIGN, 'posts': {}}
    inventory = json.loads(INVENTORY.read_text(encoding='utf8')) if INVENTORY.exists() else {'campaign_id': CAMPAIGN, 'posts': {}}
    if args.set_decision:
        pid, decision = args.set_decision
        if pid not in inventory['posts'] or decision not in ('mirror', 'skip', 'review'):
            parser.error('Use a discovered post ID and a decision of mirror, skip, or review')
        if not args.reason.strip():
            parser.error('--reason is required when recording a decision')
        set_decision(inventory, manifest, pid, decision, args.reason)
        save_inventory(inventory, manifest)
        print(pid, decision)
        return
    params = {'filter[campaign_id]': CAMPAIGN, 'filter[is_draft]': 'false', 'sort': '-published_at', 'page[count]': '10', 'fields[post]': 'title,url,published_at,edited_at'}
    url = 'https://www.patreon.com/api/posts?' + urlencode(params)
    report = {'new': [], 'updated': [], 'unchanged': [], 'failed': [], 'warnings': {}, 'seen': [], 'skipped': [], 'review': []}
    page = 0
    while url:
        if urlsplit(url).hostname != 'www.patreon.com' or urlsplit(url).path != '/api/posts':
            raise ValueError('Unexpected pagination URL')
        cache = CACHE / f'inventory-batch-{page}.json'
        if not args.cached:
            cache.write_bytes(fetch(url))
        data = json.loads(cache.read_text(encoding='utf8'))
        report['reported_total'] = data.get('meta', {}).get('pagination', {}).get('total')
        media = {x['id']: x for x in data.get('included', []) if x['type'] == 'media'}
        for post in data['data']:
            pid = post['id']
            report['seen'].append(pid)
            a = post['attributes']
            entry = remember_post(inventory, post, manifest)
            if entry['decision'] not in ('mirror', 'skip', 'review'):
                raise ValueError('Unknown inventory decision for ' + pid)
            if entry['decision'] != 'mirror':
                report['skipped' if entry['decision'] == 'skip' else 'review'].append(pid)
                continue
            if args.discover_only:
                continue
            old = manifest['posts'].get(pid)
            slug = old['slug'] if old else re.sub(r'[^a-z0-9]+', '-', a['title'].lower()).strip('-') + '-' + pid
            dest = ROOT / 'content/blog' / slug / 'index.md'
            try:
                if dest.exists() and (not old or digest(dest.read_text(encoding='utf8')) != old['file_hash']):
                    raise ValueError('Local edits detected; reconcile manually before syncing')
                detail_url = 'https://www.patreon.com/api/posts/' + pid + '?include=campaign,images,attachments_media,audio,media'
                detail_cache = CACHE / ('post-' + pid + '.json')
                if not args.cached:
                    detail_cache.write_bytes(fetch(detail_url))
                detail = json.loads(detail_cache.read_text(encoding='utf8'))
                post = detail['data']
                a = post['attributes']
                media = {x['id']: x for x in detail.get('included', []) if x['type'] == 'media'}
                renderer = Renderer(post, media)
                body = renderer.render()
                image_order = (a.get('post_metadata') or {}).get('image_order') or []
                cover = '/images/blog/' + pid + '/' + str(image_order[0]) + '.jpg' if image_order else next(iter(renderer.images), '')
                fields = {'title': entry.get('title_override') or a['title'], 'date': a['published_at'], 'updated': a.get('edited_at') or a['published_at']}
                text = '+++\n' + ''.join(k + ' = ' + json.dumps(v, ensure_ascii=False) + '\n' for k, v in fields.items())
                text += '[extra]\npatreon_id = ' + json.dumps(pid) + '\npatreon_url = ' + json.dumps(a['url']) + '\ncover = ' + json.dumps(cover) + '\n+++\n\n' + body
                file_hash = digest(text)
                status = 'unchanged' if old and old['file_hash'] == file_hash else ('updated' if old else 'new')
                for path, raw in renderer.images.items():
                    image_path = ROOT / 'static' / path.lstrip('/')
                    image_path.parent.mkdir(parents=True, exist_ok=True)
                    if not image_path.exists() or image_path.read_bytes() != raw:
                        image_path.write_bytes(raw)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(text, encoding='utf8')
                manifest['posts'][pid] = {'slug': slug, 'url': a['url'], 'published_at': a['published_at'], 'file_hash': file_hash}
                MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
                report[status].append(pid)
                entry.pop('last_error', None)
                entry['last_synced_at'] = datetime.now(timezone.utc).isoformat()
                if renderer.warnings:
                    report['warnings'][pid] = renderer.warnings
                print(status, pid, a['title'], flush=True)
            except Exception as exc:
                entry['last_error'] = str(exc)
                report['failed'].append({'id': pid, 'reason': str(exc)})
                print('FAILED', pid, str(exc), flush=True)
        save_inventory(inventory, manifest)
        url = data.get('links', {}).get('next') if args.all else None
        page += 1
        if url:
            time.sleep(1)
    report['scope'] = 'all' if args.all else 'latest 10'
    report['missing_from_listing'] = sorted(set(manifest['posts']) - set(report['seen'])) if args.all else []
    if args.all:
        inventory['last_full_scan'] = datetime.now(timezone.utc).isoformat()
        inventory['reported_total'] = report['reported_total']
        inventory['missing_from_listing'] = sorted(set(inventory['posts']) - set(report['seen']))
    save_inventory(inventory, manifest)
    (CACHE / 'sync-report.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    print(json.dumps({k: v for k, v in report.items() if k != 'seen'}, indent=2))
    if report['failed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
