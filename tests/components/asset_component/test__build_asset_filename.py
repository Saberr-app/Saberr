import hashlib
from dataclasses import dataclass

import pytest


def _hashed(url: str, ext: str = "") -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest() + ext


@dataclass
class Case:
    id: str
    url: str
    expected_result: str


CASES = [
    Case(id="hashes url and keeps short extension",
         url="https://example.com/path/image.png",
         expected_result=_hashed("https://example.com/path/image.png", ".png")),
    Case(id="drops overlong extension",  # suffix > 10 chars -> dropped
         url="https://example.com/file.somelongextension",
         expected_result=_hashed("https://example.com/file.somelongextension")),
    Case(id="no extension",
         url="https://example.com/resource",
         expected_result=_hashed("https://example.com/resource")),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__build_asset_filename(case: Case, asset_component):
    assert asset_component._build_asset_filename(case.url) == case.expected_result
