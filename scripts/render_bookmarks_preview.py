from jinja2 import Environment, FileSystemLoader, select_autoescape
import os
from datetime import datetime

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), '..', 'app', 'templates')

def to_jst(value, fmt='%Y年%m月%d日'):
    try:
        return value.strftime(fmt)
    except Exception:
        return value

env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(['html', 'xml'])
)
env.filters['to_jst'] = to_jst

documents = [
    {
        'id': 1,
        'title': 'サンプル記事1',
        'domain': 'example.com',
        'created_at': datetime(2025,9,27,12,34),
        'updated_at': datetime(2025,9,27,12,34),
        'thumbnail_url': None,
        'short_summary': 'これは**要約**です。\n改行もあります。',
        'content_text': '本文の最初の部分。'*10,
        'bookmarked': True,
        'classifications': [ { 'primary_category': 'テック/AI', 'tags': ['AI','LLM','Python'] } ]
    },
    {
        'id': 2,
        'title': 'サンプル記事2',
        'domain': 'example.org',
        'created_at': datetime(2025,9,26,9,0),
        'updated_at': datetime(2025,9,26,9,0),
        'thumbnail_url': None,
        'short_summary': None,
        'content_text': '別記事の本文'*20,
        'bookmarked': True,
        'classifications': []
    }
]

t = env.get_template('bookmarks_only.html')
html = t.render(documents=documents, page=1, per_page=20, total=2)
# print a snippet around data-md-inline occurrences
for line in html.splitlines():
    if 'data-md-inline' in line or 'data-md-autostart' in line:
        print(line)

# Also write to file for manual inspection if needed
out = os.path.join(os.path.dirname(__file__), 'preview.html')
with open(out, 'w', encoding='utf-8') as f:
    f.write(html)
print('Wrote preview to', out)
