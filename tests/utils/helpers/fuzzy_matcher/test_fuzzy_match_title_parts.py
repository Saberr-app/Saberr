from dataclasses import dataclass

import pytest

from constants import Encoding, Resolution, VideoSource
from dto.nyaa_item import ReleaseTitleParts
from utils.helpers.fuzzy_matcher import fuzzy_match_title_parts


def expect(title=None, group=None, season=None, episode=None, version=None,
           language=None, resolution=None, source: VideoSource = VideoSource.OTHER,
           encoding=None, batch=False) -> ReleaseTitleParts:
    """Build the expected ReleaseTitleParts; source defaults to OTHER, batch to False."""
    return ReleaseTitleParts(
        release_group=group,
        title=title,
        season_number=season,
        episode_number=episode,
        version_number=version,
        language_code=language,
        resolution=resolution,
        source=source,
        encoding=encoding,
        is_batch=batch,
        repack_indicator=False,
        censorship_status=False,
        missing_required=not all([group, title, episode, resolution, source, encoding]),
    )


@dataclass
class Case:
    raw: str
    expected: ReleaseTitleParts


# A diverse, currently-passing sample of real Nyaa release titles and the parts they resolve into.
CASES = [
    Case(raw='[ChuySub] Majokko Megu-chan - Episode 48',
         expected=expect(group='ChuySub', title='Majokko Megu-chan', episode=48)),
    Case(raw="[Yameii] Isekai Office Worker: The Other World's Books Depend on the Bean Counter - S01E08 [English Dub] [CR WEB-DL 1080p H264 AAC] [A5876386] (Isekai no Sata wa Shachiku Shidai)",
         expected=expect(group='Yameii', title="Isekai Office Worker: The Other World's Books Depend on the Bean Counter", season=1, episode=8, language='EN', resolution=Resolution.P1080, source=VideoSource.CRUNCHYROLL, encoding=Encoding.AVC)),
    Case(raw='[Headpatter] Chained Soldier Season 2 (BD 1080p x264 8-bit Opus) [Dual Audio] | Mato Seihei no Slave 2',
         expected=expect(group='Headpatter', title='Chained Soldier', season=2, language='dual', resolution=Resolution.P1080, encoding=Encoding.AVC, batch=True)),
    Case(raw='[HnY] BeyWheelz 05 - Race! BeyWheelz Grand Prix (1080p).mkv',
         expected=expect(group='HnY', title='BeyWheelz', episode=5, resolution=Resolution.P1080)),
    Case(raw='[FoundYears] The Warrior Princess and the Barbaric King S01E01-E08 (CR WEB-DL 1080p AVC AAC) [Dual-Audio] | Himekishi wa Barbaroi no Yome',
         expected=expect(group='FoundYears', title='The Warrior Princess and the Barbaric King', season=1, episode=1, language='dual', resolution=Resolution.P1080, source=VideoSource.CRUNCHYROLL, encoding=Encoding.AVC, batch=True)),
    Case(raw='[ASW] Quanzhi Fashi S7 - 05 [1080p HEVC x265 10Bit][AAC]',
         expected=expect(group='ASW', title='Quanzhi Fashi', season=7, episode=5, resolution=Resolution.P1080, encoding=Encoding.HEVC)),
    Case(raw='Versatile Mage S07E05 1080p CR WEB-DL AAC2.0 H 264-VARYG (Quanzhi Fashi IV, Multi-Subs)',
         expected=expect(group='VARYG', title='Versatile Mage', season=7, episode=5, resolution=Resolution.P1080, source=VideoSource.CRUNCHYROLL, encoding=Encoding.AVC)),
    Case(raw='{Bite Me Bitch} Bang Dream!-Episode Of Roselia Movies BDRemux',
         expected=expect(group='Bite Me Bitch', title='Bang Dream!-Episode Of Roselia Movies', batch=True)),
    Case(raw='[SonicMaster] Jujutsu Kaisen - Hidden Inventory Premature Death - The Movie (2025) [BDRemux 1080p AVC TrueHD 5.1 E-AC3 2.0] [Dual-Audio] [v2]',
         expected=expect(group='SonicMaster', title='Jujutsu Kaisen - Hidden Inventory Premature Death - The Movie', version=2, language='dual', resolution=Resolution.P1080, encoding=Encoding.AVC)),
    Case(raw='[Erai-raws] Megami ~Isekai Tensei Nani ni Naritai Desu ka~ Ore ~Yuusha no Rokkotsu de~ - 11 [1080p CR WEBRip HEVC AAC][MultiSub][79CD8D58]',
         expected=expect(group='Erai-raws', title='Megami ~Isekai Tensei Nani ni Naritai Desu ka~ Ore ~Yuusha no Rokkotsu de~', episode=11, resolution=Resolution.P1080, source=VideoSource.CRUNCHYROLL, encoding=Encoding.HEVC)),
    Case(raw='[ToonsHub] MARRIAGETOXIN S01E08 1080p CR WEB-DL MULTi AAC2.0 H.264 (Multi-Audio, Multi-Subs)',
         expected=expect(group='ToonsHub', title='MARRIAGETOXIN', season=1, episode=8, language='multi', resolution=Resolution.P1080, source=VideoSource.CRUNCHYROLL, encoding=Encoding.AVC)),
    Case(raw='[Tasokare] mono S01 (BD 1080p Opus AV1)',
         expected=expect(group='Tasokare', title='mono', season=1, resolution=Resolution.P1080, encoding=Encoding.AV1, batch=True)),
    Case(raw='[SubsPlus+] Lastame - S02E11 (ADN WEB-DL 1080p AVC AAC) | The Most Heretical Last Boss Queen: From Villainess to Savior',
         expected=expect(group='SubsPlus+', title='Lastame', season=2, episode=11, resolution=Resolution.P1080, source=VideoSource.ADN, encoding=Encoding.AVC)),
    Case(raw='[yolerejiju] My Dress-Up Darling Season 2 (S02) (BD 1080p x265 Opus - DDP - AAC) [Multi-Audio] | Sono Bisque Doll wa Koi wo Suru',
         expected=expect(group='yolerejiju', title='My Dress-Up Darling', season=2, language='multi', resolution=Resolution.P1080, encoding=Encoding.HEVC, batch=True)),
    Case(raw='Lupin III - TV Special Collection (1989-2019) [14-Special Collection] (BDRip 1080p x265 HEVC OPUS 2.0x2)(Dual Audio-Complete)[MICO XD]',
         expected=expect(title='Lupin III - TV Special Collection', language='dual', resolution=Resolution.P1080, encoding=Encoding.HEVC, batch=True)),
    Case(raw='[WBDP] Dimension W (Complete) [BD][1080p-FLAC][HEVC]',
         expected=expect(group='WBDP', title='Dimension W', resolution=Resolution.P1080, encoding=Encoding.HEVC, batch=True)),
    Case(raw='[SubsPlus+] Farming Life in Another World - S02E11 (AMZN WEB-DL 1080p AVC AAC) | Isekai Nonbiri Nouka',
         expected=expect(group='SubsPlus+', title='Farming Life in Another World', season=2, episode=11, resolution=Resolution.P1080, source=VideoSource.AMAZON, encoding=Encoding.AVC)),
    Case(raw='[Commie] Ace of the Diamond act II ~Second Season~ - 11 [BCDBACB0].mkv',
         expected=expect(group='Commie', title='Ace of the Diamond act II ~Second Season~', episode=11)),
    Case(raw='JUJUTSU KAISEN S02 MULTi 1080p DSNP WEB-DL AAC2.0 H.264-Tsundere-Raws (READNFO, VF, FRENCH, SUBFRENCH, VOSTFR, Multi Subs, Multi Audio, Sorcery Fight, JJK, Jujutsu Kaisen (TV), Jujutsu Kaisen S2)',
         expected=expect(group='Tsundere-Raws', title='JUJUTSU KAISEN', season=2, language='FR', resolution=Resolution.P1080, source=VideoSource.DISNEY_PLUS, encoding=Encoding.AVC, batch=True)),
    Case(raw='[BonoboSubs][4k]Renegade Immortal - Xian Ni Episode 145',
         expected=expect(group='BonoboSubs', title='Renegade Immortal - Xian Ni', episode=145, resolution=Resolution.P2160)),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.raw[:50])
def test_fuzzy_match_title_parts(case: Case):
    assert fuzzy_match_title_parts(case.raw) == case.expected
