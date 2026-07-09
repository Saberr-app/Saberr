from dataclasses import dataclass
from types import SimpleNamespace

import pytest


def track(track_type, *, file_size=None, duration=None, language=None):
    return SimpleNamespace(track_type=track_type, file_size=file_size, duration=duration, language=language)


def media(*tracks):
    return SimpleNamespace(tracks=list(tracks))


@dataclass
class Case:
    id: str
    media_info: object
    expected_result: tuple


CASES = [
    # duration is milliseconds -> rounded seconds; audio languages collected in order
    Case(id="general and audio tracks are resolved",
         media_info=media(track("General", file_size=1048576, duration=90000),
                          track("Audio", language="eng"), track("Audio", language="jpn")),
         expected_result=(1048576, 90, ["eng", "jpn"])),
    Case(id="missing duration stays None",
         media_info=media(track("General", file_size=500, duration=None)),
         expected_result=(500, None, [])),
    # audio tracks without a language are ignored
    Case(id="audio track without language is skipped",
         media_info=media(track("General", file_size=10, duration=2000),
                          track("Audio", language=None), track("Audio", language="eng")),
         expected_result=(10, 2, ["eng"])),
    Case(id="no general track leaves size and duration None",
         media_info=media(track("Audio", language="eng")),
         expected_result=(None, None, ["eng"])),
    Case(id="no tracks at all",
         media_info=media(),
         expected_result=(None, None, [])),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__resolve_media_metadata(case: Case, make_processing_component, mocker):
    mocker.patch("pymediainfo.MediaInfo.parse", return_value=case.media_info)
    component = make_processing_component()

    assert component._resolve_media_metadata("/some/file.mkv") == case.expected_result
