from dataclasses import dataclass, field
from datetime import datetime
from xml.etree import ElementTree

from dto.settings import ReleaseGroup
from constants import ReleaseTitlePart, Resolution, VideoSource, Encoding, ReleaseCriteriaProperty
from dto.anilist import AnilistAnimeMinimal
from utils.helpers.fuzzy_matcher import (fuzzy_match_resolution, fuzzy_match_encoding,
                                         fuzzy_match_language_code, fuzzy_match_video_source)
from utils.helpers.text_helpers import get_size_in_bytes, get_human_readable_size, clean_text_with_html_tags


@dataclass
class NyaaItem:
    title: str
    link: str
    web_link: str
    seeders: int
    leechers: int
    downloads: int
    magnet_hash: str
    category_id: str
    category: str
    size: int
    comments: int
    remake: bool
    trusted: bool
    description: str
    created_at: datetime
    source_xml: str

    @classmethod
    def from_xml(cls, item_element: ElementTree.Element) -> 'NyaaItem':
        ns = {"nyaa": "https://nyaa.si/xmlns/nyaa"}
        title = item_element.find('title').text
        link = item_element.find('link').text
        web_link = item_element.find('guid').text
        seeders = int(item_element.find('nyaa:seeders', ns).text)
        leechers = int(item_element.find('nyaa:leechers', ns).text)
        downloads = int(item_element.find('nyaa:downloads', ns).text)
        magnet_hash = item_element.find('nyaa:infoHash', ns).text
        category_id = item_element.find('nyaa:categoryId', ns).text
        category = item_element.find('nyaa:category', ns).text
        size = get_size_in_bytes(item_element.find('nyaa:size', ns).text)
        comments = int(item_element.find('nyaa:comments', ns).text)
        remake = item_element.find('nyaa:remake', ns).text == 'Yes'
        trusted = item_element.find('nyaa:trusted', ns).text == 'Yes'
        description = item_element.find('description').text
        created_at_str = item_element.find('pubDate').text
        created_at = datetime.strptime(created_at_str, '%a, %d %b %Y %H:%M:%S %z')

        return cls(title=title, link=link, web_link=web_link,
                   seeders=seeders, leechers=leechers,
                   downloads=downloads, magnet_hash=magnet_hash,
                   category_id=category_id, category=category,
                   size=size, comments=comments,
                   remake=remake, trusted=trusted,
                   description=description, created_at=created_at,
                   source_xml=ElementTree.tostring(item_element, encoding='unicode'))

    @classmethod
    def from_xml_string(cls, xml_data: str) -> 'NyaaItem':
        root = ElementTree.fromstring(xml_data)
        return cls.from_xml(root)

    @classmethod
    def many_from_xml_string(cls, xml_data: str) -> list['NyaaItem']:
        root = ElementTree.fromstring(xml_data)
        items = []
        for item_elem in root.find('channel').findall('item'):
            item = cls.from_xml(item_elem)
            items.append(item)
        return items

    def __repr__(self):
        return f"NyaaItem({self.clean_description})"

    @property
    def size_str(self) -> str:
        return get_human_readable_size(self.size)

    @property
    def clean_description(self) -> str:
        return clean_text_with_html_tags(self.description, extra_patterns=r'<!\[CDATA\[|\]\]>')


@dataclass
class ReleaseTitleParts:
    release_group: str | None
    title: str | None
    season_number: int | None
    episode_number: int | None
    version_number: int | None
    language_code: str | None
    repack_indicator: bool | None
    resolution: Resolution | None
    source: VideoSource | None
    encoding: Encoding | None
    censorship_status: bool | None

    missing_required: bool
    is_batch: bool = False

    @property
    def search_title(self) -> str:
        if self.season_number and self.season_number > 1:
            return f'{self.title} Season {self.season_number}'
        elif self.season_number and self.season_number == 0:
            return f'{self.title} Specials'
        return self.title

    @classmethod
    def from_dict(cls, data: dict, missing_required: bool = False) -> 'ReleaseTitleParts':
        return cls(release_group=data.get(ReleaseTitlePart.RELEASE_GROUP.value),
                   title=data.get(ReleaseTitlePart.TITLE.value),
                   season_number=ReleaseTitleParts.int_or_none(data.get(ReleaseTitlePart.SEASON_NUMBER.value)),
                   episode_number=ReleaseTitleParts.int_or_none(data.get(ReleaseTitlePart.EPISODE_NUMBER.value)),
                   version_number=ReleaseTitleParts.int_or_none(data.get(ReleaseTitlePart.VERSION_NUMBER.value)),
                   language_code=fuzzy_match_language_code(data.get(ReleaseTitlePart.LANGUAGE_CODE.value)),
                   repack_indicator=ReleaseTitleParts.bool_or_none(data.get(ReleaseTitlePart.REPACK_INDICATOR.value)),
                   resolution=fuzzy_match_resolution(data.get(ReleaseTitlePart.RESOLUTION.value)),
                   source=fuzzy_match_video_source(data.get(ReleaseTitlePart.SOURCE.value)),
                   encoding=fuzzy_match_encoding(data.get(ReleaseTitlePart.ENCODING.value)),
                   censorship_status=ReleaseTitleParts.bool_or_none(data.get(ReleaseTitlePart.CENSORSHIP_STATUS.value)),
                   missing_required=missing_required)

    @staticmethod
    def int_or_none(value: str | None) -> int | None:
        if value is None or value.strip() == "":
            return None
        try:
            return int(value.strip())
        except ValueError:
            return None

    @staticmethod
    def bool_or_none(value: str | None) -> bool | None:
        if value is None or value.strip() == "":
            return False
        return True


@dataclass
class RawTorrent:
    nyaa_item: NyaaItem
    title_parts: ReleaseTitleParts | None
    release_group_settings: ReleaseGroup | None

    anilist_anime_min: AnilistAnimeMinimal | None
    anilist_episode_number: int | None  # resolved episode number relative to anilist entry, not the torrent title

    episode_part: int = 0  # equivalent to db torrent.episode_part, 0 indicates non-part
    episode_part_ceiling: int = 0  # equivalent to db torrent.episode_part_ceiling, 0 indicates non-part
    db_episode_id: int | None = None
    other_db_episode_ids: list[int] = field(default_factory=list)
    db_torrent_id: int | None = None
    other_episodes_db_torrent_ids: list[int] = field(default_factory=list)
    db_download_id: int | None = None

    is_batch_torrent: bool = False
    require_identifying_data_on_override: bool = False
    selected: bool = False  # flag to indicate whether this torrent was selected as the current best candidate
    superseded: bool = False  # other better torrents were downloaded previously or selected
    not_tracked: bool = False
    discarded: bool = False  # either episode was set to auto-discard or torrent was manually discarded

    profile_shortcomings: list[ReleaseCriteriaProperty] = field(default_factory=list)

    _notes: list[tuple[str, bool]] = field(default_factory=list)

    # temp attributes
    t_to_process: bool = False
    t_tracked_anilist_id: int | None = None
    t_relations_anilist_id: int | None = None

    @property
    def notes(self) -> list[tuple[str, bool]]:
        return self._notes

    def add_note(self, note: str, error: bool = False):
        self._notes.append((note, error))
