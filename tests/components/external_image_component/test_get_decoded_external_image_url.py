from dataclasses import dataclass
from urllib.parse import quote

import pytest

from common.exceptions import ExternalImageURLDecodeException

_ANILIST = "https://s4.anilist.co/file/anilistcdn/media/cover.png"
_TVDB = "https://artworks.thetvdb.com/banners/v4/episode/1.jpg"


@dataclass
class Case:
    id: str
    encoded: str
    expected_result: str | None = None
    expected_exception: type[Exception] | None = None


CASES = [
    Case(id="round trips an allowed anilist url", encoded=quote(_ANILIST, safe=""), expected_result=_ANILIST),
    Case(id="round trips an allowed tvdb url", encoded=quote(_TVDB, safe=""), expected_result=_TVDB),
    Case(id="empty input is rejected", encoded="", expected_exception=ExternalImageURLDecodeException),
    Case(id="disallowed host is rejected",
         encoded=quote("https://evil.com/a.png", safe=""), expected_exception=ExternalImageURLDecodeException),
    Case(id="disallowed extension is rejected",
         encoded=quote("https://s4.anilist.co/file/x.txt", safe=""),
         expected_exception=ExternalImageURLDecodeException),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_get_decoded_external_image_url(case: Case, image_component):
    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            image_component.get_decoded_external_image_url(case.encoded)
        return
    assert image_component.get_decoded_external_image_url(case.encoded) == case.expected_result
