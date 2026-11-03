#!/usr/bin/env python3
"""Convert the three audited Feishu snapshots to ordinary Hugo page bundles.

Input files and API responses stay outside the public repository. Re-run only
after fetching the approved source documents and their media with lark-cli.
"""
import argparse
import copy
import hashlib
import html
import json
from pathlib import Path
import re
import shutil
import xml.etree.ElementTree as ET

POSTS = [
    (1, 'simplify-knowledge-workflow', 'Q3ZZwZitJidFe8k5xPscxctynYF', ['工作方式', '知识管理']),
    (2, 'hallmark-ai-design', 'XXmLwPH0HimH5Qkh0MNc4Oz0nRg', ['AI 工具', '产品观察']),
    (3, 'longcat-2-5-analysis', 'MFJAwOjUriDKPwkvs5HcqfQRnPW', ['大模型', '产品观察']),
]


def escape(text):
    return re.sub(r'([\\`*_{}\[\]|#!])', r'\\\1', html.escape(text, quote=False))


def plain(node):
    out = node.text or ''
    for child in node:
        out += ('\n' if child.tag == 'br' else plain(child)) + (child.tail or '')
    return out


def inline(node):
    out = escape(node.text or '')
    for child in node:
        value = inline(child)
        if child.tag == 'b':
            value = '<strong>' + value + '</strong>'
        elif child.tag == 'em':
            value = '<em>' + value + '</em>'
        elif child.tag == 'code':
            value = '<code>' + html.escape(plain(child)) + '</code>'
        elif child.tag == 'a':
            value = '<a href="' + html.escape(child.attrib['href'], quote=True) + '">' + value + '</a>'
        elif child.tag == 'br':
            value = '<br>'
        elif child.tag not in ('p', 'li'):
            raise ValueError(f'Unsupported inline element: {child.tag}')
        out += value + escape(child.tail or '')
    return out


def block(node, image_names):
    tag = node.tag
    if tag == 'title':
        return ''
    if tag == 'p':
        return inline(node)
    if re.fullmatch(r'h[1-6]', tag):
        return '#' * int(tag[1]) + ' ' + inline(node)
    if tag == 'img':
        return f'![]({image_names[node.attrib["src"]]})'
    if tag == 'pre':
        code = plain(node)
        fence = '`' * max(3, max((len(m) + 1 for m in re.findall(r'`+', code)), default=3))
        return fence + 'text\n' + code + '\n' + fence
    if tag in ('ul', 'ol'):
        rows = []
        for i, li in enumerate(node, 1):
            assert li.tag == 'li'
            prefix = f'{i}. ' if tag == 'ol' else '- '
            content = ET.Element('li')
            content.text = li.text
            nested = []
            for child in li:
                if child.tag in ('ul', 'ol'):
                    nested.append(child)
                else:
                    content.append(copy.deepcopy(child))
            rows.append(prefix + inline(content))
            for child in nested:
                rows.extend(' ' * len(prefix) + line for line in block(child, image_names).splitlines())
        return '\n'.join(rows)
    if tag == 'table':
        rows = []
        for tr in node.iter('tr'):
            cells = []
            for td in tr:
                cells.append('<br>'.join(inline(p) for p in td if p.tag == 'p'))
            rows.append('| ' + ' | '.join(cells) + ' |')
        assert rows
        columns = len(next(node.iter('tr')))
        rows.insert(1, '| ' + ' | '.join(['---'] * columns) + ' |')
        return '\n'.join(rows)
    if tag == 'hr':
        return '---'
    raise ValueError(f'Unsupported block: {tag}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('audit_dir', type=Path)
    parser.add_argument('--imported-at', required=True, help='Actual import date, YYYY-MM-DD')
    args = parser.parse_args()
    site = Path(__file__).resolve().parents[1]
    manifest = []
    for number, slug, wiki, tags in POSTS:
        snapshot = args.audit_dir / f'article-{number}-latest.json'
        response = json.loads(snapshot.read_text())
        assert response['ok'] is True
        document = response['data']['document']
        root = ET.fromstring('<root>' + document['content'] + '</root>')
        title = plain(root.find('title'))
        folder = site / 'content' / 'posts' / slug
        folder.mkdir(parents=True, exist_ok=True)
        image_names = {}
        images = []
        for i, image in enumerate(root.iter('img'), 1):
            original = list((args.audit_dir / 'assets').glob(f'article-{number}-{i}.*'))
            assert len(original) == 1
            filename = f'image-{i:02d}' + original[0].suffix
            shutil.copy2(original[0], folder / filename)
            image_names[image.attrib['src']] = filename
            images.append({'file': filename, 'sha256': hashlib.sha256(original[0].read_bytes()).hexdigest()})
        metadata = {
            'title': title, 'draft': False, 'weight': number,
            'tags': tags, 'importedAt': args.imported_at,
            'sourceURL': f'https://ucnbjaetidak.feishu.cn/wiki/{wiki}',
            'cover': {'image': images[0]['file'], 'hiddenInSingle': True},
        }
        body = '\n\n'.join(block(node, image_names) for node in root if node.tag != 'title')
        (folder / 'index.md').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n\n' + body.rstrip() + '\n')
        manifest.append({
            'slug': slug, 'title': title, 'source_url': metadata['sourceURL'],
            'revision': document['revision_id'], 'imported_at': args.imported_at,
            'images': images, 'tables': len(list(root.iter('table'))),
            'code_blocks': len(list(root.iter('pre'))),
        })
    (site / 'content-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print('Imported:', len(manifest), 'articles;', sum(len(p['images']) for p in manifest), 'images')


if __name__ == '__main__':
    main()
