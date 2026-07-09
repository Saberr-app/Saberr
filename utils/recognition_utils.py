from dto.settings import ReleaseGroup
from constants import ReleaseGroupFilterType
from dto.nyaa_item import ReleaseTitleParts


def get_matched_release_group_in_torrent_title(torrent_title: str,
                                               release_groups_map: dict[str, ReleaseGroup]) -> ReleaseGroup | None:
    matched_release_group = None
    for _, release_group in release_groups_map.items():
        if release_group.unique_filter.filter_type == ReleaseGroupFilterType.STARTS_WITH:
            if torrent_title.lower().startswith(release_group.unique_filter.value.lower()):
                matched_release_group = release_group
        elif release_group.unique_filter.filter_type == ReleaseGroupFilterType.CONTAINS:
            if release_group.unique_filter.value.lower() in torrent_title.lower():
                matched_release_group = release_group
        else:
            raise ValueError(f"Invalid filter type: {release_group.unique_filter.filter_type}")
    return matched_release_group


def extract_release_title_parts_from_torrent(torrent_title: str,
                                             release_group_settings: ReleaseGroup) -> ReleaseTitleParts | None:
    match, match_dict, missing_required = None, {}, True
    for regex in release_group_settings.regexes:
        match_ = regex.pattern.match(torrent_title)
        if not match_:
            continue
        match_dict = match_.groupdict()
        missing_required = not all(match_dict[part.value]
                                   for part in regex.required_pattern_groups)
        if not missing_required:
            match = match_
            break
        elif not match:
            # regexes are sorted by priority, if none are a perfect match, then at least try to keep the first match
            match = match_
    if not match:
        return
    parts = ReleaseTitleParts.from_dict(match_dict, missing_required=missing_required)
    parts.encoding = parts.encoding or release_group_settings.default_encoding
    parts.resolution = parts.resolution or release_group_settings.default_resolution
    parts.language_code = parts.language_code or release_group_settings.default_language_code
    parts.version_number = parts.version_number or 1
    parts.repack_indicator = parts.repack_indicator or False
    parts.censorship_status = parts.censorship_status or False
    return parts
