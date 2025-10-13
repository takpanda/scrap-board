import re
from pathlib import Path


def test_style_css_contains_modal_gpu_rules():
    path = Path("app/static/css/style.css")
    assert path.exists(), "app/static/css/style.css not found"
    text = path.read_text(encoding="utf-8")

    # Check for will-change declaration scoped to data-modal-dialog
    assert re.search(r"\[data-modal-dialog\][\s\S]*will-change:\s*transform,\s*opacity", text), "will-change rule for [data-modal-dialog] not found"

    # Check for translateZ(0)
    assert re.search(r"\[data-modal-dialog\][\s\S]*transform:\s*translateZ\(0\)", text), "transform: translateZ(0) rule for [data-modal-dialog] not found"

    # Check for transition/animation guidance: ensure there's a rule limiting animations to transform or opacity
    # We look for 'transition' that mentions transform or opacity in the context of [data-modal-dialog]
    assert re.search(r"\[data-modal-dialog\][\s\S]*transition:[\s\S]*(transform|opacity)", text), "transition mentioning transform or opacity inside [data-modal-dialog] not found"


def test_modal_transition_not_width_or_height():
    path = Path("app/static/css/style.css")
    text = path.read_text(encoding="utf-8")

    # Ensure there's not a transition rule that animates width or height globally on [data-modal-dialog]
    modal_block = re.search(r"\[data-modal-dialog\][\s\S]*?\n\}", text)
    if modal_block:
        block_text = modal_block.group(0)
        assert not re.search(r"transition:[^;]*width|transition:[^;]*height", block_text), "Found transition animating width/height in [data-modal-dialog] block"
    else:
        # If no modal block, fail the test above already will capture missing rules
        assert True
