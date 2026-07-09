import base64
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import pytest

from components.external_image_component import ExternalImageComponent

_MEDIA_PREFIX = "https://s4.anilist.co/file/anilistcdn/media/"
_TVDB_PREFIX = "https://artworks.thetvdb.com/banners/v4/episode/"
_PREFIXES = ExternalImageComponent.KNOWN_URL_PREFIXES


def _expected(image_url: str, subfolder: str, encode_target: str, data_dir: str) -> Path:
    filename_base = base64.urlsafe_b64encode(encode_target.encode()).decode()
    ext = Path(urlparse(image_url).path).suffix
    return Path(data_dir) / "images" / subfolder / f"{filename_base}{ext}"


@dataclass
class Case:
    id: str
    url: str
    subfolder: str       # mapped folder for the matched prefix ("" when none)
    encode_target: str   # the portion of the url that gets base64'd into the filename


CASES = [
    Case(id="known anilist media prefix -> subfolder + trimmed encode",
         url=_MEDIA_PREFIX + "cover.png", subfolder=_PREFIXES[_MEDIA_PREFIX], encode_target="cover.png"),
    Case(id="known tvdb episode prefix",
         url=_TVDB_PREFIX + "123.jpg", subfolder=_PREFIXES[_TVDB_PREFIX], encode_target="123.jpg"),
    Case(id="unknown prefix -> flat folder, full url encoded",
         url="https://s4.anilist.co/other/x.png", subfolder="",
         encode_target="https://s4.anilist.co/other/x.png"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__build_image_file_path(case: Case, image_component, tmp_path):
    result = image_component._build_image_file_path(case.url)
    assert result == _expected(case.url, case.subfolder, case.encode_target, str(tmp_path))
