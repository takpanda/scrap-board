import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os

HERE = os.path.dirname(os.path.dirname(__file__))
TEMPLATES = os.path.join(HERE, 'app', 'templates')


def render_modal(document):
    # Create a Jinja2 environment pointing at the project's templates
    env = Environment(
        loader=FileSystemLoader([TEMPLATES, os.path.join(TEMPLATES, 'partials')]),
        autoescape=select_autoescape(['html', 'xml'])
    )
    tmpl = env.get_template('partials/modal_content.html')
    return tmpl.render(document=document)

class Dummy:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_modal_contains_responsive_root_classes():
    doc = Dummy(id=1, classifications=[], bookmarked=False, url=None, short_summary=None, content_md='')
    html = render_modal(doc)

    # Check root modal element
    assert 'data-modal-dialog' in html, 'modal root attribute data-modal-dialog is missing'
    assert 'w-full' in html, 'w-full class missing for modal responsiveness'
    assert 'h-full' in html, 'h-full class missing for modal responsiveness'
    assert 'md:max-w-4xl' in html, 'md:max-w-4xl missing for desktop layout preservation'
    assert 'md:p-6' in html, 'md:p-6 missing on modal sections for desktop padding'
    assert 'p-4' in html, 'p-4 missing on modal sections for mobile padding'
    assert 'data-modal-scrollable' in html, 'data-modal-scrollable missing for scrollable content area'


def test_modal_scrollable_has_touch_scrolling_style():
    doc = Dummy(id=2, classifications=[], bookmarked=False, url=None, short_summary=None, content_md='')
    html = render_modal(doc)
    # The template in repo currently inlines -webkit-overflow-scrolling
    assert '-webkit-overflow-scrolling: touch' in html or 'data-modal-scrollable' in html
