"""GRC exports must label placeholder control IDs as a demo mapping."""

from __future__ import annotations

import pytest

from app.services.grc.control_mappings import DEMO_MAPPING_PLATFORMS, mapping_disclosure


@pytest.mark.parametrize("platform", ["vanta", "drata", "secureframe", "Vanta"])
def test_third_party_platforms_are_marked_demo(platform: str) -> None:
    disclosure = mapping_disclosure(platform)
    assert disclosure["mapping_status"] == "demo"
    assert "placeholder" in disclosure["mapping_notice"]
    assert "not real" in disclosure["mapping_notice"]


def test_generic_platform_is_native() -> None:
    disclosure = mapping_disclosure("generic")
    assert disclosure["mapping_status"] == "native"


def test_demo_set_covers_every_third_party_adapter() -> None:
    assert DEMO_MAPPING_PLATFORMS == {"vanta", "drata", "secureframe"}
