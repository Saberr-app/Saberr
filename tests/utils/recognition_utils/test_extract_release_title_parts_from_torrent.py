from dataclasses import dataclass

import pytest

from config import config
from constants import Encoding, Resolution, VideoSource
from dto.nyaa_item import ReleaseTitleParts
from utils.recognition_utils import extract_release_title_parts_from_torrent

_GROUPS = config.release_groups_map
_UNSET = object()  # "not present in the title" -> expect the group's configured default


# `extract_release_title_parts_from_torrent` fills missing fields from the group's configured defaults
# (and treats an unversioned release as v1). Mirror that here by reading the same group config, so these
# expectations track data/release_groups.json instead of hardcoding its current values.
def expect(release_group, title, episode_number, resolution=_UNSET, *, season_number=None,
           version_number=1, language_code=_UNSET, repack_indicator=False,
           source: VideoSource = VideoSource.OTHER, encoding=_UNSET,
           censorship_status=False, missing_required=False):
    group = _GROUPS[release_group]
    return ReleaseTitleParts(
        release_group=release_group, title=title, season_number=season_number,
        episode_number=episode_number, version_number=version_number,
        language_code=group.default_language_code if language_code is _UNSET else language_code,
        repack_indicator=repack_indicator,
        resolution=group.default_resolution if resolution is _UNSET else resolution,
        source=source,
        encoding=group.default_encoding if encoding is _UNSET else encoding,
        censorship_status=censorship_status, missing_required=missing_required)


@dataclass
class Case:
    id: str
    group_name: str
    title: str
    expected_result: ReleaseTitleParts | None


CASES = [
    # Erai-raws: captures source + encoding from the bracketed spec
    Case(id="erai-amzn-avc", group_name="Erai-raws",
         title="[Erai-raws] Nippon Sangoku - 09 [540p AMZN WEB-DL AVC EAC3][MultiSub][7BBD7C88]",
         expected_result=expect("Erai-raws", "Nippon Sangoku", 9,
                                Resolution.P540, source=VideoSource.AMAZON, encoding=Encoding.AVC)),
    Case(id="erai-dsnp-hevc", group_name="Erai-raws",
         title="[Erai-raws] Yozakura-san Chi no Daisakusen 2nd Season - 08 "
               "[1080p DSNP WEBRip HEVC AAC][MultiSub][620CB232]",
         expected_result=expect("Erai-raws", "Yozakura-san Chi no Daisakusen 2nd Season", 8,
                                Resolution.P1080, source=VideoSource.DISNEY_PLUS, encoding=Encoding.HEVC)),
    Case(id="erai-repack", group_name="Erai-raws",
         title="[Erai-raws] Akane-banashi - 04 (REPACK) [1080p NF WEBRip HEVC AAC][MultiSub][FBE1C1D8]",
         expected_result=expect("Erai-raws", "Akane-banashi", 4, Resolution.P1080,
                                source=VideoSource.NETFLIX, encoding=Encoding.HEVC, repack_indicator=True)),
    Case(id="erai-v2", group_name="Erai-raws",
         title="[Erai-raws] Dorohedoro Season 2 - 01v2 [1080p NF WEBRip HEVC EAC3][MultiSub][93CDEFDB]",
         expected_result=expect("Erai-raws", "Dorohedoro Season 2", 1, Resolution.P1080, version_number=2,
                                source=VideoSource.NETFLIX, encoding=Encoding.HEVC)),

    # DKB: SxxExx form, no source group (-> OTHER)
    Case(id="dkb-basic", group_name="DKB",
         title="[DKB] Akane-banashi - S01E09 [1080p][HEVC x265 10bit][Multi-Subs][weekly]",
         expected_result=expect("DKB", "Akane-banashi", 9, Resolution.P1080, season_number=1,
                                encoding=Encoding.HEVC)),
    Case(id="dkb-short-title", group_name="DKB",
         title="[DKB] MAO - S01E09 [1080p][HEVC x265 10bit][Multi-Subs][weekly]",
         expected_result=expect("DKB", "MAO", 9, Resolution.P1080, season_number=1, encoding=Encoding.HEVC)),
    Case(id="dkb-two-word-title", group_name="DKB",
         title="[DKB] Kill Ao - S01E08 [1080p][HEVC x265 10bit][Multi-Subs][weekly]",
         expected_result=expect("DKB", "Kill Ao", 8, Resolution.P1080, season_number=1, encoding=Encoding.HEVC)),
    Case(id="dkb-bracket-version", group_name="DKB",
         title="[DKB] Kijin Gentoushou - S01E21 [1080p][V2][HEVC x265 10bit][weekly]",
         expected_result=expect("DKB", "Kijin Gentoushou", 21, Resolution.P1080, season_number=1,
                                version_number=2, encoding=Encoding.HEVC)),

    # SubsPlease: no encoding/source in title -> group default encoding, source OTHER
    Case(id="subsplease-720", group_name="SubsPlease",
         title="[SubsPlease] Ace of Diamond Act II S2 - 09 (720p) [B4C7D629].mkv",
         expected_result=expect("SubsPlease", "Ace of Diamond Act II S2", 9, Resolution.P720)),
    Case(id="subsplease-480", group_name="SubsPlease",
         title="[SubsPlease] Tsue to Tsurugi no Wistoria S2 - 08 (480p) [4585E94A].mkv",
         expected_result=expect("SubsPlease", "Tsue to Tsurugi no Wistoria S2", 8, Resolution.P480)),
    Case(id="subsplease-1080", group_name="SubsPlease",
         title="[SubsPlease] Niwatori Fighter - 12 (1080p) [A651BA8D].mkv",
         expected_result=expect("SubsPlease", "Niwatori Fighter", 12, Resolution.P1080)),
    Case(id="subsplease-long-title-v2", group_name="SubsPlease",
         title="[SubsPlease] Otonari no Tenshi-sama ni Itsunomanika Dame Ningen ni Sareteita Ken S2 - 01v2 (720p) "
               "[D44919B5].mkv",
         expected_result=expect("SubsPlease",
                                "Otonari no Tenshi-sama ni Itsunomanika Dame Ningen ni Sareteita Ken S2", 1,
                                Resolution.P720, version_number=2)),

    # Judas: parenthetical English alt-name stripped from title
    Case(id="judas-alt-name-stripped", group_name="Judas",
         title="[Judas] Kami no Niwatsuki Kusunoki-tei (Kusunoki's Garden of Gods) - S01E09 "
               "[1080p][HEVC x265 10bit][Multi-Subs] (Weekly)",
         expected_result=expect("Judas", "Kami no Niwatsuki Kusunoki-tei", 9, Resolution.P1080,
                                season_number=1, encoding=Encoding.HEVC)),
    Case(id="judas-uppercase-title", group_name="Judas",
         title="[Judas] NEEDY GIRL OVERDOSE - S01E09 [1080p][HEVC x265 10bit][Multi-Subs] (Weekly)",
         expected_result=expect("Judas", "NEEDY GIRL OVERDOSE", 9, Resolution.P1080, season_number=1,
                                encoding=Encoding.HEVC)),
    Case(id="judas-version", group_name="Judas",
         title="[Judas] Digimon Beatbreak - S01E01v2 [1080p][HEVC x265 10bit][Multi-Subs] (Weekly)",
         expected_result=expect("Judas", "Digimon Beatbreak", 1, Resolution.P1080, season_number=1,
                                version_number=2, encoding=Encoding.HEVC)),
    Case(id="judas-uncensored-s2", group_name="Judas",
         title="[Judas] Mato Seihei no Slave (Chained Soldier) - S02E01 "
               "[Uncensored][1080p][HEVC x265 10bit][Multi-Subs] (Weekly)",
         expected_result=expect("Judas", "Mato Seihei no Slave", 1, Resolution.P1080, season_number=2,
                                encoding=Encoding.HEVC, censorship_status=True)),

    # ASW: encoding captured from "[1080p HEVC ...]"
    Case(id="asw-basic", group_name="ASW",
         title="[ASW] Ace of Diamond Act II S2 - 09 [1080p HEVC x265 10Bit][AAC]",
         expected_result=expect("ASW", "Ace of Diamond Act II S2", 9, Resolution.P1080, encoding=Encoding.HEVC)),
    Case(id="asw-single-word", group_name="ASW",
         title="[ASW] Niwatori Fighter - 12 [1080p HEVC x265 10Bit][AAC]",
         expected_result=expect("ASW", "Niwatori Fighter", 12, Resolution.P1080, encoding=Encoding.HEVC)),
    Case(id="asw-version", group_name="ASW",
         title="[ASW] Yuusha-kei ni Shosu - 01v2 [1080p HEVC x265 10Bit][AAC]",
         expected_result=expect("ASW", "Yuusha-kei ni Shosu", 1, Resolution.P1080, version_number=2,
                                encoding=Encoding.HEVC)),

    # SubsPlus+: the romaji/full title lives after the "|" separator; the leading name is ignored
    Case(id="subsplus-title-after-pipe", group_name="SubsPlus+",
         title="[SubsPlus+] Hell Mode - S02E11 (ADN WEB-DL 1080p AVC AAC) | HELL MODE: The Hardcore Gamer "
               "Dominates in Another World with Garbage Balancing",
         expected_result=expect("SubsPlus+",
                                "HELL MODE: The Hardcore Gamer Dominates in Another World with Garbage Balancing",
                                11, Resolution.P1080, season_number=2, source=VideoSource.ADN,
                                encoding=Encoding.AVC)),
    Case(id="subsplus-v2", group_name="SubsPlus+",
         title="[SubsPlus+] The World Is Dancing - S01E07v2 (ADN WEB-DL 1080p AVC AAC) | World Is Dancing",
         expected_result=expect("SubsPlus+", "World Is Dancing", 7, Resolution.P1080, season_number=1,
                                version_number=2, source=VideoSource.ADN, encoding=Encoding.AVC)),
    # no "|" separator -> falls back to the leading name
    Case(id="subsplus-uncensored-no-pipe", group_name="SubsPlus+",
         title="[SubsPlus+] Yowayowa Sensei - S01E12 (ADN WEB-DL 1080p AVC AAC) (Uncensored)",
         expected_result=expect("SubsPlus+", "Yowayowa Sensei", 12, Resolution.P1080, season_number=1,
                                source=VideoSource.ADN, encoding=Encoding.AVC, censorship_status=True)),

    # VARYG: group tag is a suffix; the parenthetical romaji title wins when there is one
    Case(id="varyg-paren-title", group_name="VARYG",
         title="The Cat and the Dragon S01E12 The Cat and the Royal Capital Festival 1080p CR WEB-DL AAC2.0 "
               "H.264-VARYG (Neko to Ryuu, Multi-Subs)",
         expected_result=expect("VARYG", "Neko to Ryuu", 12, Resolution.P1080, season_number=1,
                                source=VideoSource.CRUNCHYROLL, encoding=Encoding.AVC)),
    # trailing parens hold only audio/sub tags -> title comes from the head of the release name
    Case(id="varyg-tag-only-parens", group_name="VARYG",
         title="BLACK TORCH S01E11 Black or White 1080p CR WEB-DL MULTi AAC2.0 H.264-VARYG "
               "(Multi-Audio, Multi-Subs)",
         expected_result=expect("VARYG", "BLACK TORCH", 11, Resolution.P1080, season_number=1,
                                source=VideoSource.CRUNCHYROLL, encoding=Encoding.AVC)),
    Case(id="varyg-repack", group_name="VARYG",
         title="One Piece S01E1177 A Despicable Hostage Game-Sommerss Brazen Demands REPACK 1080p CR WEB-DL "
               "AAC2.0 H.264-VARYG (Multi-Subs)",
         expected_result=expect("VARYG", "One Piece", 1177, Resolution.P1080, season_number=1,
                                source=VideoSource.CRUNCHYROLL, encoding=Encoding.AVC, repack_indicator=True)),
    # "HIDI" is HIDIVE's tag in these release names
    Case(id="varyg-hidi-source-no-parens", group_name="VARYG",
         title="HELL MODE S02E11 THE LIBERATED 1080p HIDI WEB-DL AAC2.0 H.264-VARYG",
         expected_result=expect("VARYG", "HELL MODE", 11, Resolution.P1080, season_number=2,
                                source=VideoSource.HIDIVE, encoding=Encoding.AVC)),

    # ToonsHub: same suffix-tag layout as VARYG, but bracket-prefixed
    Case(id="toonshub-paren-title", group_name="ToonsHub",
         title="[ToonsHub] The Cat and the Dragon S01E12 1080p CR WEB-DL AAC2.0 H.264 (Neko to Ryuu, Multi-Subs)",
         expected_result=expect("ToonsHub", "Neko to Ryuu", 12, Resolution.P1080, season_number=1,
                                source=VideoSource.CRUNCHYROLL, encoding=Encoding.AVC)),
    Case(id="toonshub-tag-only-parens", group_name="ToonsHub",
         title="[ToonsHub] BLACK TORCH S01E11 1080p CR WEB-DL DUAL AAC2.0 H.264 (Dual-Audio, Multi-Subs)",
         expected_result=expect("ToonsHub", "BLACK TORCH", 11, Resolution.P1080, season_number=1,
                                source=VideoSource.CRUNCHYROLL, encoding=Encoding.AVC)),
    Case(id="toonshub-repack-uncensored", group_name="ToonsHub",
         title="[ToonsHub] KAMUI Hes Behind You S01E08 REPACK 1080p UNCENSORED AMZN WEB-DL DDP2.0 H.264 "
               "(Ushiro no Shoumen Kamui-san, Multi-Subs)",
         expected_result=expect("ToonsHub", "Ushiro no Shoumen Kamui-san", 8, Resolution.P1080, season_number=1,
                                source=VideoSource.AMAZON, encoding=Encoding.AVC, repack_indicator=True,
                                censorship_status=True)),
    # unmapped source tag (BILI) -> OTHER
    Case(id="toonshub-hevc-unknown-source", group_name="ToonsHub",
         title="[ToonsHub] That Time I Got Reincarnated as a Slime S04E22 1080p BILI WEB-DL AAC2.0 H.265 "
               "(Tensei Shitara Slime Datta Ken, Multi-Subs)",
         expected_result=expect("ToonsHub", "Tensei Shitara Slime Datta Ken", 22, Resolution.P1080,
                                season_number=4, encoding=Encoding.HEVC)),
    # long-running shows use absolute "EP####" numbering with no season token
    Case(id="toonshub-absolute-numbering", group_name="ToonsHub",
         title="[ToonsHub] One Piece EP1177 1080p NF WEB-DL AAC2.0 H.264 (Multi-Subs)",
         expected_result=expect("ToonsHub", "One Piece", 1177, Resolution.P1080,
                                source=VideoSource.NETFLIX, encoding=Encoding.AVC)),
    Case(id="toonshub-absolute-numbering-paren-title", group_name="ToonsHub",
         title="[ToonsHub] Detective Conan EP1204 1080p CR WEB-DL AAC2.0 H.264 (Meitantei Conan, Multi-Subs)",
         expected_result=expect("ToonsHub", "Meitantei Conan", 1204, Resolution.P1080,
                                source=VideoSource.CRUNCHYROLL, encoding=Encoding.AVC)),
    Case(id="toonshub-absolute-numbering-2160p-hevc", group_name="ToonsHub",
         title="[ToonsHub] One Piece EP1164 2160p BILI WEB-DL AAC2.0 H.265 (Multi-Subs)",
         expected_result=expect("ToonsHub", "One Piece", 1164, Resolution.P2160, encoding=Encoding.HEVC)),
    Case(id="toonshub-specials-season-zero", group_name="ToonsHub",
         title="[ToonsHub] Kaiju No 8 S00E05 The Vice Captains Troubles 1080p CR WEB-DL MULTi AAC2.0 H.264 "
               "(Multi-Audio, Multi-Subs)",
         expected_result=expect("ToonsHub", "Kaiju No 8", 5, Resolution.P1080, season_number=0,
                                source=VideoSource.CRUNCHYROLL, encoding=Encoding.AVC)),

    # batch / unparseable titles -> None
    Case(id="erai-episode-range-batch", group_name="Erai-raws",
         title="[Erai-raws] Dandelion - 01 ~ 07 [1080p NF WEBRip HEVC EAC3][MultiSub] [BATCH]",
         expected_result=None),
    Case(id="erai-no-episode", group_name="Erai-raws",
         title="[Erai-raws] Food Court de Mata Ashita [1080p CR WEBRip HEVC][MultiSub] (unofficial batch)",
         expected_result=None),
    Case(id="dkb-season-batch", group_name="DKB",
         title="[DKB] Jaku-Chara Tomozaki-kun - (Season 02) [1080p][HEVC x265 10bit][Multi-Subs][Batch]",
         expected_result=None),
    Case(id="subsplease-episode-range-batch", group_name="SubsPlease",
         title="[SubsPlease] MF Ghost (25-37) (1080p) [Batch]",
         expected_result=None),
    Case(id="judas-season-batch", group_name="Judas",
         title="[Judas] Tokyo Revengers (Season 01) [BD 1080p][HEVC x265 10bit][Dual-Audio][Multi-Subs] (Batch)",
         expected_result=None),
    Case(id="asw-no-episode-batch", group_name="ASW",
         title="[ASW] Engage Kiss [1080p HEVC x265 10Bit][AAC] (Batch)",
         expected_result=None),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_extract_release_title_parts_from_torrent(case: Case, release_groups_map):
    result = extract_release_title_parts_from_torrent(case.title, release_groups_map[case.group_name])
    assert result == case.expected_result
