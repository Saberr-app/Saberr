from dataclasses import dataclass
from urllib.parse import urlparse

import pytest


@dataclass
class Case:
    id: str
    url: str
    expected_result: bool


CASES = [
    Case(id="anilist subdomain png allowed", url="https://s4.anilist.co/file/cover.png", expected_result=True),
    Case(id="anilist apex allowed", url="https://anilist.co/x.webp", expected_result=True),
    Case(id="tvdb jpg allowed", url="https://artworks.thetvdb.com/banners/1.jpg", expected_result=True),
    Case(id="non-http scheme rejected", url="ftp://s4.anilist.co/cover.png", expected_result=False),
    Case(id="disallowed host rejected", url="https://example.com/cover.png", expected_result=False),
    Case(id="disallowed extension rejected", url="https://s4.anilist.co/file/cover.txt", expected_result=False),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__is_allowed_external_image_url(case: Case, image_component):
    assert image_component._is_allowed_external_image_url(urlparse(case.url)) is case.expected_result
