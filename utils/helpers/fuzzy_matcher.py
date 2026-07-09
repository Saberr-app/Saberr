import re
from typing import TYPE_CHECKING

from constants import Encoding, Resolution, VideoSource

if TYPE_CHECKING:
    from dto.nyaa_item import ReleaseTitleParts


def _contains_token(text: str, keyword: str) -> bool:
    return re.search(rf'(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])', text) is not None


def fuzzy_match_encoding(encoding: str) -> Encoding | None:
    if not encoding:
        return None
    encoding_map = {
        Encoding.HEVC: ["hevc", "h.265", "h265", "x265"],
        Encoding.AVC: ["avc", "h264", "h.264", "x264"],
        Encoding.AV1: ["av1"],
    }
    encoding_lower = encoding.lower()
    for enc, keywords in encoding_map.items():
        if any(_contains_token(encoding_lower, keyword) for keyword in keywords):
            return enc
    return None


def fuzzy_match_resolution(resolution: str) -> Resolution | None:
    if not resolution:
        return None
    resolution_map = {
        Resolution.P2160: ["2160p", "2160", "4k", "3840x2160"],
        Resolution.P1080: ["1080p", "1080", "fullhd", "full hd", "fhd", "1920x1080"],
        Resolution.P720: ["720p", "720", "hd", "1280x720"],
        Resolution.P540: ["540p", "540", "960x540"],
        Resolution.P480: ["480p", "480", "sd", "640x480"],
    }
    resolution_lower = resolution.lower()
    for res, keywords in resolution_map.items():
        if any(_contains_token(resolution_lower, keyword) for keyword in keywords):
            return res
    return None


def fuzzy_match_video_source(source: str) -> VideoSource | None:
    if not source:
        return VideoSource.OTHER
    source_map = {
        VideoSource.CRUNCHYROLL: ["crunchyroll", "crunchy", "cr"],
        VideoSource.NETFLIX: ["netflix", "nflx", "nf"],
        VideoSource.AMAZON: ["amazon", "prime", "amzn"],
        VideoSource.DISNEY_PLUS: ["disney+", "disney plus", "disney", "dplus", "dsnp"],
        VideoSource.ADN: ["adn", "anime digital network"],
        VideoSource.HIDIVE: ["hidive", "hdv"],
        VideoSource.HULU: ["hulu"]
    }
    source_lower = source.lower()
    for src, keywords in source_map.items():
        if any(_contains_token(source_lower, keyword) for keyword in keywords):
            return src
    return VideoSource.OTHER


def fuzzy_match_language_code(language_code: str) -> str:
    if not language_code:
        return language_code
    language_map = {
        "EN": ["english", "eng", "en"],
        "JP": ["japanese", "jpn", "jap", "ja", "jp"],
        "FR": ["french", "francais", "vf", "vff", "fre", "fr"],
        "DE": ["german", "deutsch", "ger", "de"],
        "IT": ["italian", "italiano", "ita", "it"],
        "ES": ["spanish", "espanol", "latino", "spa", "es"],
        "PT": ["portuguese", "por", "pt"],
        "RU": ["russian", "rus", "ru"],
        "CN": ["chinese", "mandarin", "cantonese", "zho", "ca", "cn"],
        "KO": ["korean", "kor", "ko"],
    }
    language_lower = language_code.lower()
    for code, keywords in language_map.items():
        if any(_contains_token(language_lower, keyword) for keyword in keywords):
            return code
    return language_lower


# AI mess from here


_GROUP_RE = re.compile(r'^\s*[\[{]([^]}]+)[]}]\s*')

_CODEC = (r'(?:x?26[45]|h\.?\s?26[45]|hevc|avc|av1|xvid|divx|'
          r'aac(?:\d\.\d)?|flac|opus|e-?ac-?3|ac3|dts(?:-?hd)?|true-?hd|'
          r'dd[p+]?(?:\d\.\d)?)')
_SCENE_GROUP_RE = re.compile(rf'{_CODEC}-([A-Za-z][A-Za-z0-9-]+)(?=\s*(?:\(|$))', re.I)

_HASH_RE = re.compile(r'\[[0-9A-Fa-f]{8}]')
_EXT_RE = re.compile(r'\.(?:mkv|mp4|avi|m2ts|ts)\s*$', re.I)

_DASH = r'[-–—]'

_TYPE_KW = r'(?:Specials?|OVAs?|ONAs?|OADs?|Movies?|SP|NCED|NCOP|PV|Recap)'
_VER = r'(?:v\d+)?'

_EPISODE_PATTERNS = [
    (re.compile(rf'\bS(\d{{1,2}})E(\d{{1,3}})(?:{_DASH}E?\d{{1,3}})?{_VER}\b', re.I), 1, 2),
    (re.compile(rf'\bS\d{{1,2}}\s*{_DASH}\s*(\d{{1,3}}){_VER}\b', re.I), None, 1),
    (re.compile(rf'\bEpisode\s+(\d{{1,3}}){_VER}\b', re.I), None, 1),
    (re.compile(rf'\b{_TYPE_KW}\s+(\d{{1,3}}){_VER}\b', re.I), None, 1, 1),
    (re.compile(rf'\s{_DASH}\s(\d{{1,3}}){_VER}\b'), None, 1),
    (re.compile(rf'(?<!Season)\s(\d{{1,3}})\s{_DASH}\s'), None, 1),
    (re.compile(rf'\s{_DASH}\s*(?:complete|batch)\b', re.I), None, None),
]

_BRACKET_RE = re.compile(r'[\[({]')
_VERSION_RE = re.compile(r'\[v(\d+)]|(?<![A-Za-z])v(\d+)(?![A-Za-z0-9])', re.I)
_RESOLUTION_RE = re.compile(r'(?<![a-z0-9])(\d{3,4}p|\d{3,4}x\d{3,4}|[48]k)(?![a-z0-9])', re.I)
_TECH_START_RE = re.compile(
    rf'\b(?:\d{{3,4}}p|\d{{3,4}}x\d{{3,4}}|[48]k|multi|dual|{_CODEC}|'
    r'web-?dl|webrip|blu-?ray|bd(?:rip|remux)|hdtv|dvdrip|remux)\b',
    re.I,
)
_H26X_RE = re.compile(r'\bH[\s.]?26([45])\b', re.I)
_LEADING_TECH_TAG_RE = re.compile(r'^(?:\s*\[[^]]*(?:\d{3,4}p|[48]k)[^]]*])*\s*', re.I)
_TRAILING_TECH_RE = re.compile(
    r'\s*(?:BD|BDRip|BDRemux|BluRay|Blu-Ray|Remux|WEB|WEB-?DL|WEBRip)\s*$', re.I
)
# noinspection RegExpUnnecessaryNonCapturingGroup
_RANGE_RE = re.compile(
    rf'(?:E\d{{1,3}}(\s?){_DASH}\1E?\d{{1,3}}'
    rf'|(?<![\d.SsEe])\d{{1,3}}{_DASH}\d{{1,3}}(?![\d.]))',
    re.I,
)
_BATCH_KW_RE = re.compile(r'\b(?:batch|complete)\b', re.I)
_SEASON_RE = re.compile(r'\b(?:Season\s+\d{1,2}|\d{1,2}(?:st|nd|rd|th)\s+Season|S\d{1,2}(?!\s*E?\d))\b', re.I)
_COLLECTION_RE = re.compile(r'\b(?:movies|films|episodes|specials|ovas|onas|oads|recaps)\b', re.I)
_SEASON_PARSE_RE = re.compile(r'\bSeason\s+(\d{1,2})\b|\bS(\d{1,2})\b(?!\s*E?\d)', re.I)

_SUB_AFTER_RE = re.compile(r'[\s.\-]?subs?\b')


def _extract_episode(segment: str) -> tuple[int | None, int | None, int | None]:
    season = episode = boundary = None
    for pattern, season_group, episode_group, *rest in _EPISODE_PATTERNS:
        match = pattern.search(segment)
        if not match:
            continue
        boundary_group = rest[0] if rest else None
        cut = match.start(boundary_group) if boundary_group is not None else match.start()
        if boundary is None:
            season = int(match.group(season_group)) if season_group else None
            episode = int(match.group(episode_group)) if episode_group else None
            boundary = cut
        else:
            boundary = min(boundary, cut)
    return season, episode, boundary


def _extract_season(segment: str) -> tuple[int | None, int | None]:
    season = boundary = None
    for match in _SEASON_PARSE_RE.finditer(segment):
        if boundary is None:
            season = int(match.group(1) or match.group(2))
            boundary = match.start()
    return season, boundary


def _detect_batch(text: str, episode_number: int | None) -> bool:
    if _BATCH_KW_RE.search(text) or _RANGE_RE.search(text):
        return True
    if episode_number is None and (_SEASON_RE.search(text) or _COLLECTION_RE.search(text)):
        return True
    return False


def _audio_languages(text: str) -> set[str]:
    languages: set[str] = set()
    for match in re.finditer(r'[A-Z][A-Za-z]*', text):
        token = match.group()
        code = fuzzy_match_language_code(token)
        if code == token.lower():
            continue
        following = text[match.end():].lower()
        if _SUB_AFTER_RE.match(following) or text[:match.start()].lower().endswith(('sub', 'vost')):
            continue
        languages.add(code)
    return languages


def _detect_language(tech_region: str) -> str | None:
    languages = _audio_languages(tech_region)
    if len(languages) >= 2:
        return 'multi'
    if languages:
        return next(iter(languages))
    lowered = tech_region.lower()
    if re.search(r'\bdual\b', lowered):
        return 'dual'
    if re.search(r'\bmulti[\s.-]?audio\b', lowered) or re.search(r'\bmulti\b(?![\s.-]?sub)', lowered):
        return 'multi'
    return None


def _clean_title(title: str) -> str | None:
    title = re.sub(r'^\[(?:\d{3,4}p|[48]k)]\s*', '', title.strip(), flags=re.I)
    previous = None
    while previous != title:
        previous = title
        title = _TRAILING_TECH_RE.sub('', title)
    title = re.sub(r'\s{2,}', ' ', title.strip(' \t-–—:|'))
    return title or None


def fuzzy_match_title_parts(release_title: str) -> 'ReleaseTitleParts':
    from dto.nyaa_item import ReleaseTitleParts
    working = _HASH_RE.sub('', _EXT_RE.sub('', release_title.replace("_", " ")))

    release_group = None
    group_match = _GROUP_RE.match(working)
    if group_match:
        release_group = group_match.group(1).strip()
        working = working[group_match.end():]

    primary = working.split('|', 1)[0]
    if release_group is None:
        scene_matches = _SCENE_GROUP_RE.findall(primary)
        if scene_matches:
            release_group = scene_matches[-1]

    title_start = _LEADING_TECH_TAG_RE.match(primary).end()
    season_number, episode_number, ep_boundary = _extract_episode(primary)
    standalone_season, season_boundary = _extract_season(primary)
    if season_number is None:
        season_number = standalone_season
    bracket = _BRACKET_RE.search(primary, title_start)
    tech = _TECH_START_RE.search(primary, title_start)
    cuts = [cut for cut in (ep_boundary, season_boundary,
                            bracket.start() if bracket else None,
                            tech.start() if tech else None) if cut is not None]
    boundary = max(min(cuts), title_start) if cuts else len(primary)

    title = _clean_title(primary[title_start:boundary])
    tech_region = primary[boundary:] + ' ' + working[len(primary):]

    version_match = _VERSION_RE.search(tech_region)
    version_number = int(version_match.group(1) or version_match.group(2)) if version_match else None

    resolution_match = _RESOLUTION_RE.search(working)
    resolution = fuzzy_match_resolution(resolution_match.group(1)) if resolution_match else None
    encoding = fuzzy_match_encoding(_H26X_RE.sub(r'H26\1', working))
    source = fuzzy_match_video_source(tech_region)
    language_code = _detect_language(tech_region)
    is_batch = _detect_batch(working, episode_number)

    return ReleaseTitleParts(
        release_group=release_group,
        title=title,
        season_number=season_number,
        episode_number=episode_number,
        version_number=version_number,
        language_code=language_code,
        resolution=resolution,
        source=source,
        encoding=encoding,
        is_batch=is_batch,
        repack_indicator=False,
        censorship_status=False,
        missing_required=not all([release_group, title, episode_number, resolution, source, encoding]),
    )
