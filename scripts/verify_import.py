#!/usr/bin/env python3
"""Verify rendered article text, image placement, asset hashes, and block counts."""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlparse
import xml.etree.ElementTree as ET


def normalize(value):
    return re.sub(r'\s+', '', value)


def collapse(events):
    result = []
    for kind, value in events:
        if kind == 'text':
            value = normalize(value)
            if not value:
                continue
            if result and result[-1][0] == 'text':
                result[-1] = ('text', result[-1][1] + value)
                continue
        result.append((kind, value))
    return result


class ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.events = []
        self.images = []
        self.counts = {'table': 0, 'pre': 0}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'div':
            if self.depth:
                self.depth += 1
            elif 'post-content' in attrs.get('class', '').split():
                self.depth = 1
        if self.depth:
            if tag in self.counts:
                self.counts[tag] += 1
            if tag == 'img':
                src = attrs['src']
                self.images.append(src)
                self.events.append(('image', Path(unquote(urlparse(src).path)).name))

    def handle_endtag(self, tag):
        if tag == 'div' and self.depth:
            self.depth -= 1

    def handle_data(self, data):
        if self.depth:
            self.events.append(('text', data))


def expected_events(node, image_names):
    if node.tag in ('title', 'colgroup'):
        return []
    if node.tag == 'img':
        return [('image', image_names[node.attrib['src']])]
    events = [('text', node.text or '')]
    for child in node:
        events.extend(expected_events(child, image_names))
        events.append(('text', child.tail or ''))
    return events


def main():
    args = argparse.ArgumentParser()
    args.add_argument('audit_dir', type=Path, nargs='?')
    audit = args.parse_args().audit_dir
    site = Path(__file__).resolve().parents[1]
    manifest = json.loads((site / 'content-manifest.json').read_text())
    for i, post in enumerate(manifest, 1):
        rendered = site / 'public' / 'posts' / post['slug'] / 'index.html'
        parser = ArticleParser()
        parser.feed(rendered.read_text())
        if audit:
            document = json.loads((audit / f'article-{i}-latest.json').read_text())['data']['document']
            root = ET.fromstring('<root>' + document['content'] + '</root>')
            assert len(list(root.iter('img'))) == len(post['images'])
            image_names = {node.attrib['src']: image['file'] for node, image in zip(root.iter('img'), post['images'])}
            expected = collapse(expected_events(root, image_names))
            actual = collapse(parser.events)
            if expected != actual:
                raise AssertionError(f'Article content or image placement differs: {post["slug"]}')
        assert parser.counts == {'table': post['tables'], 'pre': post['code_blocks']}
        assert len(parser.images) == len(post['images'])
        for url, image in zip(parser.images, post['images']):
            assert urlparse(url).path.startswith('/blog/'), url
            path = site / 'public' / unquote(urlparse(url).path).removeprefix('/blog/')
            assert hashlib.sha256(path.read_bytes()).hexdigest() == image['sha256']
        detail = 'full text and image placement match; ' if audit else ''
        print(f'PASS {post["slug"]}: {detail}{len(parser.images)} images; {post["tables"]} table; {post["code_blocks"]} code blocks')


if __name__ == '__main__':
    main()
