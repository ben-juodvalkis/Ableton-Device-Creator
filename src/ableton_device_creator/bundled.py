"""Default device templates shipped inside the package.

A pip install carries no repo checkout, so ``templates/`` relative to the
working directory only exists for someone running from a clone. These are
byte-identical copies of the repo's ``templates/`` defaults (checked by
``tests/test_bundled_templates.py``) and are what every creator and CLI command
falls back to when no template is given.
"""

from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent / "templates"

DRUM_RACK_TEMPLATE = TEMPLATES_DIR / "input_rack.adg"
SAMPLER_TEMPLATE = TEMPLATES_DIR / "sampler-rack.adg"
SIMPLER_TEMPLATE = TEMPLATES_DIR / "simpler-template.adv"
