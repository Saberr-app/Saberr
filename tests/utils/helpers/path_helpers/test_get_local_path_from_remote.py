from dataclasses import dataclass

import pytest

from utils.helpers.path_helpers import get_local_path_from_remote

B = chr(92)  # backslash, kept out of string literals for readability of Windows cases


@dataclass
class Case:
    id: str
    remote_path: str
    mapping: tuple[str, str]
    expected_result: str


CASES = [
    # --- POSIX remote -> POSIX local ---
    Case(id="posix nested path is re-rooted",
         remote_path="/downloads/Anime/ep.mkv", mapping=("/downloads", "/data/torrents"),
         expected_result="/data/torrents/Anime/ep.mkv"),
    Case(id="path equal to remote maps to local root",
         remote_path="/downloads", mapping=("/downloads", "/data/torrents"),
         expected_result="/data/torrents"),
    Case(id="trailing slash on path is normalized away",
         remote_path="/downloads/", mapping=("/downloads", "/data/torrents"),
         expected_result="/data/torrents"),
    Case(id="trailing slash on remote prefix is tolerated",
         remote_path="/downloads/a/b/c.mkv", mapping=("/downloads/", "/data/torrents"),
         expected_result="/data/torrents/a/b/c.mkv"),
    Case(id="trailing slash on local prefix is normalized away",
         remote_path="/downloads/ep.mkv", mapping=("/downloads", "/data/torrents/"),
         expected_result="/data/torrents/ep.mkv"),
    Case(id="redundant separators in path collapse",
         remote_path="/downloads/a//b/ep.mkv", mapping=("/downloads", "/data/t"),
         expected_result="/data/t/a/b/ep.mkv"),
    Case(id="identical remote and local is effectively a normpath",
         remote_path="/x/a/ep.mkv", mapping=("/x", "/x"),
         expected_result="/x/a/ep.mkv"),
    Case(id="special characters in remainder are preserved",
         remote_path="/downloads/a b/ep [1080p]{x}.mkv", mapping=("/downloads", "/data/t"),
         expected_result="/data/t/a b/ep [1080p]{x}.mkv"),

    # --- Non-matching paths pass through unchanged (original, un-normalized) ---
    Case(id="prefix lookalike does not match at boundary",
         remote_path="/downloads-old/ep.mkv", mapping=("/downloads", "/data/torrents"),
         expected_result="/downloads-old/ep.mkv"),
    Case(id="unrelated path is returned untouched",
         remote_path="/other/ep.mkv", mapping=("/downloads", "/data/torrents"),
         expected_result="/other/ep.mkv"),
    Case(id="posix match is case-sensitive",
         remote_path="/DOWNLOADS/ep.mkv", mapping=("/downloads", "/data/t"),
         expected_result="/DOWNLOADS/ep.mkv"),
    Case(id="relative input never matches an absolute remote",
         remote_path="relative/ep.mkv", mapping=("/downloads", "/data/t"),
         expected_result="relative/ep.mkv"),
    Case(id="path normalizing outside the prefix is not mapped",
         remote_path="/downloads/../secret/ep.mkv", mapping=("/downloads", "/data/t"),
         expected_result="/downloads/../secret/ep.mkv"),

    # --- Windows remote -> POSIX local ---
    Case(id="windows backslash remote is re-rooted to posix local",
         remote_path="D:" + B + "Torrents" + B + "Anime" + B + "ep.mkv",
         mapping=("D:" + B + "Torrents", "/data/torrents"),
         expected_result="/data/torrents/Anime/ep.mkv"),
    Case(id="windows match is case-insensitive",
         remote_path="d:" + B + "torrents" + B + "ep.mkv",
         mapping=("D:" + B + "Torrents", "/data/torrents"),
         expected_result="/data/torrents/ep.mkv"),
    Case(id="windows forward-slash input matches backslash remote",
         remote_path="D:/Torrents/Anime/ep.mkv",
         mapping=("D:" + B + "Torrents", "/data/torrents"),
         expected_result="/data/torrents/Anime/ep.mkv"),
    Case(id="path equal to windows remote maps to local root",
         remote_path="D:" + B + "Torrents",
         mapping=("D:" + B + "Torrents", "/data/torrents"),
         expected_result="/data/torrents"),
    Case(id="different windows drive passes through",
         remote_path="C:" + B + "Other" + B + "ep.mkv",
         mapping=("D:" + B + "Torrents", "/data/torrents"),
         expected_result="C:" + B + "Other" + B + "ep.mkv"),

    # --- POSIX remote -> Windows local (reverse direction) ---
    Case(id="posix remote is re-rooted to windows local with backslashes",
         remote_path="/data/x/ep.mkv", mapping=("/data", "E:" + B + "Media"),
         expected_result="E:" + B + "Media" + B + "x" + B + "ep.mkv"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_get_local_path_from_remote(case: Case):
    assert get_local_path_from_remote(case.remote_path, case.mapping) == case.expected_result