from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest

from constants import Encoding, Resolution, VideoSource, ReleaseCriteriaProperty as RCP
from components.operational_components.torrent_component import TorrentComponent


def _torrent(*, release_group="GroupA", encoding=Encoding.HEVC, resolution=Resolution.P1080,
             source=VideoSource.CRUNCHYROLL, language_code="eng"):
    return SimpleNamespace(release_group=release_group, encoding=encoding, resolution=resolution,
                           source=source, language_code=language_code)


@dataclass
class Case:
    id: str
    torrent_kwargs: dict = field(default_factory=dict)
    profile_kwargs: dict = field(default_factory=dict)
    expected_reasons: list = field(default_factory=list)


CASES = [
    Case(id="no preferences means no dismissals"),
    Case(id="matching torrent passes all preferences",
         profile_kwargs=dict(preferred_release_groups=["GroupA"], preferred_encodings=[Encoding.HEVC],
                             preferred_resolutions=[Resolution.P1080], preferred_sources=[VideoSource.CRUNCHYROLL],
                             preferred_language_codes=["eng"], sources_restricted=True,
                             language_codes_restricted=True)),
    Case(id="release group mismatch is dismissed",
         torrent_kwargs=dict(release_group="GroupA"), profile_kwargs=dict(preferred_release_groups=["GroupB"]),
         expected_reasons=[RCP.RELEASE_GROUP]),
    Case(id="encoding mismatch is dismissed",
         torrent_kwargs=dict(encoding=Encoding.HEVC), profile_kwargs=dict(preferred_encodings=[Encoding.AVC]),
         expected_reasons=[RCP.ENCODING]),
    Case(id="resolution mismatch is dismissed",
         torrent_kwargs=dict(resolution=Resolution.P1080), profile_kwargs=dict(preferred_resolutions=[Resolution.P720]),
         expected_reasons=[RCP.RESOLUTION]),
    Case(id="source mismatch ignored when not restricted",
         torrent_kwargs=dict(source=VideoSource.NETFLIX),
         profile_kwargs=dict(preferred_sources=[VideoSource.CRUNCHYROLL], sources_restricted=False)),
    Case(id="source mismatch dismissed when restricted",
         torrent_kwargs=dict(source=VideoSource.NETFLIX),
         profile_kwargs=dict(preferred_sources=[VideoSource.CRUNCHYROLL], sources_restricted=True),
         expected_reasons=[RCP.SOURCE]),
    Case(id="language mismatch ignored when not restricted",
         torrent_kwargs=dict(language_code="jpn"),
         profile_kwargs=dict(preferred_language_codes=["eng"], language_codes_restricted=False)),
    Case(id="language mismatch dismissed when restricted",
         torrent_kwargs=dict(language_code="jpn"),
         profile_kwargs=dict(preferred_language_codes=["eng"], language_codes_restricted=True),
         expected_reasons=[RCP.LANGUAGE_CODE]),
    Case(id="multiple mismatches are all collected",
         torrent_kwargs=dict(release_group="GroupA", resolution=Resolution.P1080),
         profile_kwargs=dict(preferred_release_groups=["GroupB"], preferred_resolutions=[Resolution.P720]),
         expected_reasons=[RCP.RELEASE_GROUP, RCP.RESOLUTION]),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_validate_torrent_candidacy(case: Case, make_profile):
    reasons = TorrentComponent._validate_torrent_candidacy(
        db_torrent=_torrent(**case.torrent_kwargs), anime_profile=make_profile(**case.profile_kwargs))
    assert reasons == case.expected_reasons
