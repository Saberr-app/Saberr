from dataclasses import dataclass
from urllib.parse import quote

import pytest

_ANILIST = "https://s4.anilist.co/file/anilistcdn/media/cover.png"
_DISALLOWED = "https://example.com/a.png"


@dataclass
class Case:
    id: str
    url: str
    expected_result: str


CASES = [
    Case(id="allowed host is percent-encoded", url=_ANILIST, expected_result=quote(_ANILIST, safe="")),
    Case(id="disallowed host returned unchanged", url=_DISALLOWED, expected_result=_DISALLOWED),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_get_encoded_external_image_url(case: Case, image_component):
    assert image_component.get_encoded_external_image_url(case.url) == case.expected_result
