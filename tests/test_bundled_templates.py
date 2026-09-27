"""The templates shipped in the package must match the repo's defaults."""

from pathlib import Path

import pytest

from ableton_device_creator import bundled
from ableton_device_creator.drum_racks import DrumRackCreator
from ableton_device_creator.sampler import SamplerCreator, SimplerCreator

REPO_TEMPLATES = Path(__file__).resolve().parents[1] / "templates"


@pytest.mark.skipif(not REPO_TEMPLATES.is_dir(), reason="needs a repo checkout")
def test_bundled_templates_match_repo_copies():
    for bundled_path in (
        bundled.DRUM_RACK_TEMPLATE,
        bundled.SAMPLER_TEMPLATE,
        bundled.SIMPLER_TEMPLATE,
    ):
        repo_path = REPO_TEMPLATES / bundled_path.name
        assert bundled_path.read_bytes() == repo_path.read_bytes(), bundled_path.name


def test_creators_default_to_bundled_templates():
    assert DrumRackCreator().template == bundled.DRUM_RACK_TEMPLATE
    assert SamplerCreator().template == bundled.SAMPLER_TEMPLATE
    assert SimplerCreator().template == bundled.SIMPLER_TEMPLATE
