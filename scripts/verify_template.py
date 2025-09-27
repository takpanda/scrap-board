from jinja2 import Environment, FileSystemLoader, TemplateSyntaxError
import sys

env = Environment(loader=FileSystemLoader('app/templates'))

try:
    tmpl = env.get_template('document_detail.html')
    print('Template parsed successfully')
except TemplateSyntaxError as e:
    print('TemplateSyntaxError:', e)
    sys.exit(1)
except Exception as e:
    print('Other error:', e)
    sys.exit(2)
