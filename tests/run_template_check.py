#!/usr/bin/env python3
import sys
from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader('app/templates'))

def make_sample_document():
    return {
        'id': 1,
        'title': 'テスト記事',
        'bookmarked': False,
        'url': 'https://example.com',
        'classifications': [
            {
                'primary_category': 'テック/AI',
                'tags': ['機械学習', 'LLM長いタグ名でオーバーフローを起こすかな']
            }
        ],
        'short_summary': '短い要約',
        'content_md': '本文のマークダウン'
    }

def main():
    tmpl = env.get_template('partials/modal_content.html')
    html = tmpl.render(document=make_sample_document())

    failed = False
    if 'title="テック/AI"' not in html:
        print('FAIL: title for primary_category not found')
        failed = True
    else:
        print('OK: primary_category title found')

    if 'dify-tag-secondary' not in html:
        print('FAIL: dify-tag-secondary not present')
        failed = True
    else:
        print('OK: dify-tag-secondary present')

    # simple content check
    if '<div class="tag-list' not in html:
        print('FAIL: tag-list container missing')
        failed = True
    else:
        print('OK: tag-list container present')

    if failed:
        sys.exit(1)
    print('All checks passed')

if __name__ == '__main__':
    main()
