import re

from common.exceptions import TorrentEpisodeCountMismatch
from constants import ShowDirectoryFormattingToken, SeasonDirectoryFormattingToken, EpisodeFormattingToken
from dto.anilist import AnilistAnime
from dto.orm_models import TrackedAnimeProcessingSettings, Torrent, TrackedAnimeEpisode, TrackedAnime
from dto.tvdb import TVDBSeries, TVDBSeriesEpisode
from utils.helpers.text_helpers import clean_path_name


def format_show_directory_name(format_: str,
                               anilist_anime: AnilistAnime,
                               tvdb_show: TVDBSeries) -> str:
    anilist_romaji_title = anilist_anime.romaji_title
    anilist_english_title = anilist_anime.english_title or anilist_romaji_title
    tvdb_english_title = (tvdb_show.english_title if tvdb_show else '') or anilist_english_title
    season = anilist_anime.season.value.title() if anilist_anime.season else 'Unknown'
    year = anilist_anime.season_year or tvdb_show.year or 'Unknown'
    values = {
        ShowDirectoryFormattingToken.ANILIST_TITLE_JAPANESE.value: anilist_anime.native_title,
        ShowDirectoryFormattingToken.ANILIST_TITLE_ROMAJI.value: anilist_romaji_title,
        ShowDirectoryFormattingToken.ANILIST_TITLE_ENGLISH.value: anilist_english_title,
        ShowDirectoryFormattingToken.TVDB_TITLE_ENGLISH.value: tvdb_english_title,
        ShowDirectoryFormattingToken.SEASON.value: season,
        ShowDirectoryFormattingToken.SEASON_YEAR.value: str(year)
    }
    return clean_path_name(format_.format(**values))


def format_season_directory_name(processing_settings: TrackedAnimeProcessingSettings, season_number: int):
    return clean_path_name(processing_settings.season_directory_name_format.format(
        **{
            SeasonDirectoryFormattingToken.SEASON_NUMBER.value: 
                str(season_number).zfill(processing_settings.season_directory_number_padding)
        }
    ))


def format_file_name(tracked_anime: TrackedAnime,
                     anilist_anime: AnilistAnime,
                     tvdb_show: TVDBSeries | None,
                     tvdb_episodes: list[TVDBSeriesEpisode],
                     db_torrents: list[Torrent]) -> str:
    # Names a single physical file represented by db_torrents (all the same file, each pointing to a
    # unique tracked_anime_episode). Branches on whether tvdb structure is enabled:
    #   raw uses the anime episode numbers
    #   tvdb uses the mapped TVDB episodes.
    processing_settings = tracked_anime.processing_settings
    torrent = db_torrents[0]  # shared release fields are identical across the list

    anilist_romaji_title = anilist_anime.romaji_title or anilist_anime.native_title
    anilist_english_title = anilist_anime.english_title or anilist_romaji_title
    tvdb_english_title = (tvdb_show.english_title if tvdb_show else '') or anilist_english_title
    season = anilist_anime.season.value.title() if anilist_anime.season else 'Unknown'
    year = anilist_anime.season_year or (tvdb_show.year if tvdb_show else None) or 'Unknown'

    values = {
        EpisodeFormattingToken.ANILIST_TITLE_JAPANESE.value: anilist_anime.native_title,
        EpisodeFormattingToken.ANILIST_TITLE_ROMAJI.value: anilist_romaji_title,
        EpisodeFormattingToken.ANILIST_TITLE_ENGLISH.value: anilist_english_title,
        EpisodeFormattingToken.TVDB_TITLE_ENGLISH.value: tvdb_english_title,
        EpisodeFormattingToken.SHOW_NAME.value: tracked_anime.show_folder_name,
        EpisodeFormattingToken.SEASON.value: season,
        EpisodeFormattingToken.SEASON_YEAR.value: str(year),
        EpisodeFormattingToken.ENCODING.value: torrent.encoding.value,
        EpisodeFormattingToken.RESOLUTION.value: torrent.resolution.value,
        EpisodeFormattingToken.RELEASE_GROUP.value: torrent.release_group,
    }

    episodes = [t.tracked_anime_episode for t in db_torrents]
    padding = processing_settings.episode_number_padding

    if not processing_settings.tracked_anime.tvdb_structure_enabled:
        # raw/anilist branch
        format_ = processing_settings.raw_episode_file_name_format
        episode_numbers = sorted(e.episode_number for e in episodes)
        # non-zero part implies a single torrent
        part_numbers = [torrent.episode_part] if (len(db_torrents) == 1 and torrent.episode_part) else None
        values[EpisodeFormattingToken.EPISODE_NUMBER.value] = _format_numbers_with_parts(
            format_, episode_numbers, part_numbers, padding)
        return clean_path_name(format_.format(**values))

    # TVDB branch
    episode_id_episode_map = {e.id: e for e in tvdb_episodes}
    resolved_episodes, part_numbers = _resolve_tvdb_episodes(db_torrents, episodes, episode_id_episode_map)

    format_ = (processing_settings.episode_file_name_format
               if any(e.title for e in resolved_episodes)
               else processing_settings.titleless_episode_file_name_format)

    numbers = [e.number for e in resolved_episodes]
    absolute_numbers = [e.absolute_number for e in resolved_episodes]
    values |= {
        EpisodeFormattingToken.SEASON_NUMBER.value:
            str(resolved_episodes[0].season_number).zfill(processing_settings.season_number_padding),
        EpisodeFormattingToken.EPISODE_NUMBER.value:
            _format_numbers_with_parts(format_, numbers, part_numbers, padding),
        EpisodeFormattingToken.ABSOLUTE_EPISODE_NUMBER.value:
            _format_numbers_with_parts(format_, absolute_numbers, part_numbers, padding, for_absolute=True),
        EpisodeFormattingToken.EPISODE_TITLE.value:
            ' / '.join(e.title for e in resolved_episodes if e.title),
    }
    return clean_path_name(format_.format(**values))


def _resolve_tvdb_episodes(db_torrents: list[Torrent],
                           episodes: list[TrackedAnimeEpisode],
                           episode_id_episode_map: dict[int, TVDBSeriesEpisode],
                           ) -> tuple[list[TVDBSeriesEpisode], list[int] | None]:
    """
    Resolve the file's torrents/anime-episodes to the TVDB episode(s) it represents and the possible part numbers.
    Raises TorrentEpisodeCountMismatch when a raw torrent part can't be evenly reconciled with the TVDB episode count.
    """
    def tvdb_episodes_for(episode_: TrackedAnimeEpisode) -> list[TVDBSeriesEpisode]:
        return sorted((episode_id_episode_map[i] for i in episode_.tvdb_episode_ids), key=lambda e: e.number)

    if len(db_torrents) == 1:
        torrent = db_torrents[0]
        episode = episodes[0]
        tvdb_episodes = tvdb_episodes_for(episode)
        tvdb_episode_count = len(tvdb_episodes)

        if torrent.episode_part:
            raw_part, raw_part_ceiling = torrent.episode_part, torrent.episode_part_ceiling
            if tvdb_episode_count == 1:
                if episode.tvdb_episode_part:
                    return tvdb_episodes, [episode.tvdb_episode_part]
                return tvdb_episodes, [raw_part]
            if raw_part_ceiling == tvdb_episode_count:
                return [tvdb_episodes[raw_part - 1]], None
            if tvdb_episode_count % raw_part_ceiling == 0:
                tvdb_episodes_per_raw_part = tvdb_episode_count // raw_part_ceiling
                return tvdb_episodes[(raw_part - 1) * tvdb_episodes_per_raw_part:
                                     raw_part * tvdb_episodes_per_raw_part], None
            if raw_part_ceiling % tvdb_episode_count == 0:
                raw_parts_per_tvdb_episode = raw_part_ceiling // tvdb_episode_count
                containing_episode_number = (raw_part + raw_parts_per_tvdb_episode - 1) // raw_parts_per_tvdb_episode
                sub_part_within_episode = ((raw_part - 1) % raw_parts_per_tvdb_episode) + 1
                return [tvdb_episodes[containing_episode_number - 1]], [sub_part_within_episode]
            raise TorrentEpisodeCountMismatch()

        if tvdb_episode_count == 1 and episode.tvdb_episode_part:
            return tvdb_episodes, [episode.tvdb_episode_part]
        return tvdb_episodes, None

    if not any(e.tvdb_episode_part for e in episodes):
        return _union_tvdb_episodes(episodes, tvdb_episodes_for), None

    distinct_tvdb_episode_ids = {i for e in episodes for i in e.tvdb_episode_ids}
    if len(distinct_tvdb_episode_ids) == 1:
        shared_episode = episode_id_episode_map[next(iter(distinct_tvdb_episode_ids))]
        present_parts = sorted(e.tvdb_episode_part for e in episodes if e.tvdb_episode_part)
        total_parts_in_episode = next(e.tvdb_episode_part_ceiling for e in episodes if e.tvdb_episode_part)
        if len(present_parts) == total_parts_in_episode:
            return [shared_episode], None
        return [shared_episode], present_parts
    return _union_tvdb_episodes(episodes, tvdb_episodes_for), None


def _union_tvdb_episodes(episodes: list[TrackedAnimeEpisode], tvdb_episodes_for) -> list[TVDBSeriesEpisode]:
    unique = {e.id: e for episode in episodes for e in tvdb_episodes_for(episode)}
    return sorted(unique.values(), key=lambda e: e.number)


def _are_continuous(numbers: list[int]) -> bool:
    numbers = sorted(numbers)
    return all(numbers[idx] - numbers[idx - 1] == 1 for idx in range(1, len(numbers)))


def _format_numbers_with_parts(format_: str, numbers: list[int], part_numbers: list[int] | None,
                               episode_number_padding: int, for_absolute: bool = False) -> str:
    episode_str = _get_episode_number_string(format_=format_, episode_numbers=numbers,
                                             episode_number_padding=episode_number_padding,
                                             are_continuous=_are_continuous(numbers), for_absolute=for_absolute)
    if part_numbers:
        episode_str += _format_part_suffix(part_numbers)
    return episode_str


def _format_part_suffix(part_numbers: list[int]) -> str:
    part_numbers = sorted(part_numbers)
    if len(part_numbers) == 1:
        return f" Part {part_numbers[0]}"
    if _are_continuous(part_numbers):
        return f" Part {part_numbers[0]}-{part_numbers[-1]}"
    return " Part " + "&".join(str(num) for num in part_numbers)


def _get_episode_number_prefix(format_: str, token: str = EpisodeFormattingToken.EPISODE_NUMBER.value) -> str:
    # extract E/e/Ep/EP prepended to EpisodeFormattingToken.EPISODE_NUMBER.value
    match = re.search(r'(EP|Ep|ep|E|e)\{' + token + r'}', format_)
    return match.group(1) if match else ''


def _get_episode_number_string(format_: str, episode_numbers: list[int], episode_number_padding: int,
                               are_continuous: bool, for_absolute: bool = False) -> str:
    episode_prefix = _get_episode_number_prefix(format_,
                                                token=EpisodeFormattingToken.ABSOLUTE_EPISODE_NUMBER.value
                                                if for_absolute else EpisodeFormattingToken.EPISODE_NUMBER.value)
    if are_continuous:
        if len(episode_numbers) > 1:
            episode_str = (f"{str(episode_numbers[0]).zfill(episode_number_padding)}"
                           f"-{episode_prefix}"
                           f"{str(episode_numbers[-1]).zfill(episode_number_padding)}")
        else:
            episode_str = str(episode_numbers[0]).zfill(episode_number_padding)
    else:
        if episode_prefix:
            episode_str = episode_prefix.join([str(num).zfill(episode_number_padding)
                                               for num in episode_numbers])
        else:
            episode_str = " & ".join([str(num).zfill(episode_number_padding)
                                     for num in episode_numbers])
    return episode_str
