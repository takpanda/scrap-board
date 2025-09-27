from jinja2 import Environment, FileSystemLoader, select_autoescape
import os

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), '..', 'app', 'templates')

def main():
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(['html', 'xml'])
    )
    # register minimal filters used by templates
    def to_jst(value, fmt='%Y-%m-%d'):
        try:
            return value.strftime(fmt)
        except Exception:
            return value

    env.filters['to_jst'] = to_jst

    templates = ['bookmarks_only.html', 'documents.html']
    for t in templates:
        try:
            tmpl = env.get_template(t)
            print(f"Loaded template: {t}")
        except Exception as e:
            print(f"Error loading {t}: {e}")

if __name__ == '__main__':
    main()
