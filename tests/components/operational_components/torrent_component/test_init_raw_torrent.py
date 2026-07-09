from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from components.operational_components.torrent_component import TorrentComponent

_COMPONENT = "components.operational_components.torrent_component"
_MATCH_GROUP = f"{_COMPONENT}.get_matched_release_group_in_torrent_title"
_EXTRACT = f"{_COMPONENT}.extract_release_title_parts_from_torrent"


@dataclass
class Case:
    id: str
    title: str = "[GroupA] Show - 01"
    release_group_matched: bool = True    # whether a release group is found
    title_parses: bool = True             # whether title parts are extracted
    expected_has_group_settings: bool = False
    expected_has_title_parts: bool = False
    expected_error_note: str | None = None
    expected_extract_called: bool = True
    expected_is_batch: bool = False


CASES = [
    Case(id="no matching release group flags an error",
         release_group_matched=False, expected_error_note="No matching release group found in torrent title.",
         expected_extract_called=False),
    Case(id="unparseable title flags an error",
         title_parses=False, expected_has_group_settings=True,
         expected_error_note="Could not parse all required details from the torrent title."),
    Case(id="successful parse populates title parts",
         expected_has_group_settings=True, expected_has_title_parts=True),
    Case(id="batch keyword in title sets the batch flag",
         title="[GroupA] Show BATCH 01-12", expected_has_group_settings=True,
         expected_has_title_parts=True, expected_is_batch=True),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_init_raw_torrent(case: Case, mocker):
    release_group = MagicMock(batch_keyword="BATCH") if case.release_group_matched else None
    match = mocker.patch(_MATCH_GROUP, return_value=release_group)
    extract = mocker.patch(_EXTRACT, return_value=MagicMock() if case.title_parses else None)

    raw = TorrentComponent.init_raw_torrent(SimpleNamespace(title=case.title))

    assert match.called
    assert (raw.release_group_settings is not None) == case.expected_has_group_settings
    assert (raw.title_parts is not None) == case.expected_has_title_parts
    assert extract.called == case.expected_extract_called
    assert raw.is_batch_torrent == case.expected_is_batch
    if case.expected_error_note is not None:
        assert raw.notes[-1] == (case.expected_error_note, True)
    else:
        assert raw.notes == []
