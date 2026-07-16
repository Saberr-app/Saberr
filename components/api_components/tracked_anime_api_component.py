from collections import defaultdict
from datetime import datetime, UTC, timedelta

from app_state import anime_relations
from common.decorators import api_component
from common.exceptions import AnilistNotFoundException, ObjectNotFoundException, QbitNotConfiguredException
from components import BaseComponent
from components.operational_components.tracked_anime_component import TrackedAnimeComponent
from components.operational_components.tracked_anime_episode_component import TrackedAnimeEpisodeComponent
from components.service_components.anilist_component import AnilistComponent
from components.service_components.qbit_component import QBitComponent
from components.service_components.anilist_list_component import AnilistListComponent
from components.service_components.anilist_airing_schedule_component import AnilistAiringScheduleComponent
from components.service_components.tvdb_component import TVDBComponent
from config import config
from constants import TrackedAnimeStatus, TVDBSeasonType, TorrentDownloadStatus, AnilistAnimeStatus
from dto.anilist import AnilistAnime, AnilistAiringScheduleItem, AnilistUserListEntry
from dto.nyaa_item import NyaaItem
from dto.orm_models import TrackedAnime, TrackedAnimeEpisode, Torrent
from api.schemas.anime_schemas import AnimeItemBase, AnimeItem, AnilistItemAiringScheduleItem
from api.schemas.tracked_anime_schemas import (
    TrackedAnimeCreateRequest, TrackedAnimeUpdateRequest, TrackedAnimeItem,
    TrackedAnimeItemWithEpisodes, TrackedAnimeListResponse, TrackedAnimeRawSettings,
    TrackedAnimeTVDBSettings, TrackedAnimeReleaseGroupSettings, TrackedAnimeReleaseProfileSettings,
    TrackedAnimeBatchArchiveRequest, TrackedAnimeBatchDeleteRequest, TrackedAnimeItemEpisode,
    TrackedAnimeItemEpisodeList, TrackedAnimeItemEpisodeDetails, TrackedAnimeEpisodeUpdateRequest,
)
from system import UNSET
from utils.helpers.text_helpers import clean_path_name


class TrackedAnimeAPIComponent(BaseComponent):

    def __init__(self):
        super().__init__()
        self._anilist_airing_schedule_component = AnilistAiringScheduleComponent()
        self._anilist_component = AnilistComponent()
        self._anilist_list_component = AnilistListComponent()
        self._qbit_component = QBitComponent()
        self._tracked_anime_component = TrackedAnimeComponent()
        self._tracked_anime_episode_component = TrackedAnimeEpisodeComponent()
        self._tvdb_component = TVDBComponent()

    @api_component
    async def create_tracked_anime(self, body: TrackedAnimeCreateRequest):
        anime = await self._anilist_component.get_anime(anilist_anime_id=body.anilist_id,)
        if anime is None:
            raise AnilistNotFoundException(f"No anime found for id: {body.anilist_id}")
        offset_map = {s.release_group_name: s.episode_number_offset
                      for s in body.release_group_settings if s.episode_number_offset}
        title_map = {s.release_group_name: s.override_match_against
                     for s in body.release_group_settings if s.override_match_against}
        created = await self._tracked_anime_component.create_tracked_anime(
            anilist_anime=anime,
            from_episode=body.from_episode,
            tvdb_structure_enabled=body.tvdb_structure_enabled,
            tvdb_season_type=body.tvdb_settings.tvdb_season_type,
            show_parent_directory=body.show_parent_directory,
            show_folder_name=clean_path_name(body.show_folder_name),
            episode_number_padding=body.episode_number_padding,
            season_number_padding=body.tvdb_settings.season_number_padding,
            season_directory_number_padding=body.tvdb_settings.season_directory_number_padding,
            season_directory_name_format=body.tvdb_settings.season_directory_name_format,
            raw_episode_file_name_format=body.raw_settings.raw_episode_file_name_format,
            episode_file_name_format=body.tvdb_settings.episode_file_name_format,
            titleless_episode_file_name_format=body.tvdb_settings.titleless_episode_file_name_format,
            release_group_overriding_title_map=title_map,
            release_group_overriding_offset_map=offset_map,
            release_profile=body.release_profile,
        )
        tracked_anime = await self._tracked_anime_component.get_tracked_anime_by_id(created.id)
        airing, user_entry = await self._hydrate_single(anime)
        return self._to_item(tracked_anime=tracked_anime, anime=anime, user_entry=user_entry,
                             airing_schedule=airing,
                             tvdb_series_id=await anime_relations.get_anilist_id_tvdb_series_id(anime.id))

    @api_component
    async def get_tracked_anime_list(self, force_freshness: bool = False,
                                     status: TrackedAnimeStatus = TrackedAnimeStatus.ACTIVE,
                                     anilist_id: int | None = None) -> TrackedAnimeListResponse:
        tracked_anime_list = await self._tracked_anime_component.get_all_tracked_anime(
            statuses=[status],
            anilist_ids=[anilist_id] if anilist_id is not None else None
        )
        anilist_ids = [ta.anilist_id for ta in tracked_anime_list]
        anime_records = await self._anilist_component.get_anime_records(anilist_anime_ids=anilist_ids,
                                                                        force_refresh=force_freshness)
        anime_map = {anime.id: anime for anime in anime_records}
        airing_map = await self._anilist_airing_schedule_component.get_future_anime_schedule_records_map(
            anilist_id_status_map={anime.id: anime.status for anime in anime_records},
            force_fetch=force_freshness
        )
        user_list = await self._anilist_list_component.get_user_anime_list(force_fetch=force_freshness) \
            if config.user_settings.anilist_user_token else None
        items = []
        for tracked_anime in tracked_anime_list:
            anime = anime_map.get(tracked_anime.anilist_id)
            if anime is None:
                continue
            items.append(self._to_item(
                tracked_anime=tracked_anime,
                anime=anime,
                user_entry=user_list.get_entry_by_anime_id(tracked_anime.anilist_id) if user_list else None,
                airing_schedule=airing_map.get(tracked_anime.anilist_id) or [],
                tvdb_series_id=await anime_relations.get_anilist_id_tvdb_series_id(tracked_anime.anilist_id),
            ))
        watching_not_tracked_count = 0
        planning_not_tracked_count = 0
        if user_list:
            watching_not_tracked_ids = user_list.current_anime_ids - set(anime_map.keys())
            planning_not_tracked_ids = user_list.planning_anime_ids - set(anime_map.keys())
            list_anime_records = await self._anilist_component.get_anime_records(
                anilist_anime_ids=watching_not_tracked_ids | planning_not_tracked_ids,
                force_refresh=force_freshness
            )
            watching_not_tracked_count = len({anime.id for anime in list_anime_records
                                              if anime.id in watching_not_tracked_ids
                                              and anime.status == AnilistAnimeStatus.RELEASING})
            planning_not_tracked_count = len({anime.id for anime in list_anime_records
                                              if anime.id in planning_not_tracked_ids
                                              and anime.status == AnilistAnimeStatus.RELEASING})

        return TrackedAnimeListResponse(tracked_anime=items,
                                        releasing_watching_not_tracked_count=watching_not_tracked_count,
                                        releasing_planning_not_tracked_count=planning_not_tracked_count)

    @api_component
    async def get_tracked_anime(self, tracked_anime_id: int,
                                force_freshness: bool = False,
                                with_episodes: bool = True) -> TrackedAnimeItemWithEpisodes:
        tracked_anime = await self._tracked_anime_component.get_tracked_anime_by_id(tracked_anime_id)
        if tracked_anime is None:
            raise ObjectNotFoundException(f"Tracked anime not found: {tracked_anime_id}")
        anime = await self._anilist_component.get_anime(anilist_anime_id=tracked_anime.anilist_id,
                                                        force_refresh=force_freshness,)
        if anime is None:
            raise AnilistNotFoundException(f"No anime found for id: {tracked_anime.anilist_id}")
        airing, user_entry = await self._hydrate_single(anime, force_freshness=force_freshness)
        base = self._to_item(tracked_anime=tracked_anime, anime=anime, user_entry=user_entry,
                             airing_schedule=airing,
                             tvdb_series_id=await anime_relations.get_anilist_id_tvdb_series_id(anime.id))
        if with_episodes:
            episodes = await self._build_episodes(tracked_anime=tracked_anime, anime=anime,
                                                  force_freshness=force_freshness)
        else:
            episodes = []
        return TrackedAnimeItemWithEpisodes(**base.model_dump(), episodes=episodes)

    @api_component
    async def update_tracked_anime(self, tracked_anime_id: int,
                                   body: TrackedAnimeUpdateRequest) -> TrackedAnimeItem:
        offset_map = {s.release_group_name: s.episode_number_offset for s in body.release_group_settings}
        title_map = {s.release_group_name: s.override_match_against for s in body.release_group_settings}
        await self._tracked_anime_component.update_tracked_anime(
            tracked_anime_id=tracked_anime_id,
            set_to_active=body.unarchive if body.unarchive is not None else UNSET,
            from_episode=body.from_episode,
            tvdb_structure_enabled=body.tvdb_structure_enabled,
            tvdb_season_type=body.tvdb_settings.tvdb_season_type,
            show_parent_directory=body.show_parent_directory,
            show_folder_name=clean_path_name(body.show_folder_name),
            episode_number_padding=body.episode_number_padding,
            season_number_padding=body.tvdb_settings.season_number_padding,
            season_directory_number_padding=body.tvdb_settings.season_directory_number_padding,
            season_directory_name_format=body.tvdb_settings.season_directory_name_format,
            raw_episode_file_name_format=body.raw_settings.raw_episode_file_name_format,
            episode_file_name_format=body.tvdb_settings.episode_file_name_format,
            titleless_episode_file_name_format=body.tvdb_settings.titleless_episode_file_name_format,
            release_group_overriding_title_map=title_map,
            release_group_overriding_offset_map=offset_map,
            release_profile=body.release_profile,
        )
        tracked_anime = await self._tracked_anime_component.get_tracked_anime_by_id(tracked_anime_id)
        if tracked_anime is None:
            raise ObjectNotFoundException(f"Tracked anime not found: {tracked_anime_id}")
        anime = await self._anilist_component.get_anime(anilist_anime_id=tracked_anime.anilist_id)
        if anime is None:
            raise AnilistNotFoundException(f"No anime found for id: {tracked_anime.anilist_id}")
        airing, user_entry = await self._hydrate_single(anime)
        return self._to_item(tracked_anime=tracked_anime, anime=anime, user_entry=user_entry,
                             airing_schedule=airing,
                             tvdb_series_id=await anime_relations.get_anilist_id_tvdb_series_id(anime.id))

    @api_component
    async def archive_tracked_anime(self, tracked_anime_id: int) -> None:
        await self._tracked_anime_component.archive_tracked_anime(tracked_anime_ids=[tracked_anime_id])

    @api_component
    async def unarchive_tracked_anime(self, tracked_anime_id: int) -> None:
        await self._tracked_anime_component.unarchive_tracked_anime(tracked_anime_ids=[tracked_anime_id])

    @api_component
    async def delete_tracked_anime(self, tracked_anime_id: int) -> None:
        await self._tracked_anime_component.delete_tracked_anime(tracked_anime_ids=[tracked_anime_id])

    @api_component
    async def batch_archive_tracked_anime(self, body: TrackedAnimeBatchArchiveRequest) -> None:
        await self._tracked_anime_component.archive_tracked_anime(anilist_ids=body.anilist_ids)

    @api_component
    async def batch_delete_tracked_anime(self, body: TrackedAnimeBatchDeleteRequest) -> None:
        await self._tracked_anime_component.delete_tracked_anime(anilist_ids=body.anilist_ids)

    @api_component
    async def get_tracked_anime_episodes(self, tracked_anime_id: int,
                                         offset: int,
                                         limit: int,
                                         force_freshness: bool) -> TrackedAnimeItemEpisodeList:
        tracked_anime = await self._tracked_anime_component.get_tracked_anime_by_id(tracked_anime_id)
        if tracked_anime is None:
            raise ObjectNotFoundException(f"Tracked anime not found: {tracked_anime_id}")
        anime = await self._anilist_component.get_anime(anilist_anime_id=tracked_anime.anilist_id,
                                                        force_refresh=force_freshness,)
        episodes = await self._build_episodes(tracked_anime=tracked_anime, anime=anime,
                                              force_freshness=force_freshness,
                                              lowest=offset + 1, highest=offset + limit)
        return TrackedAnimeItemEpisodeList(episodes=episodes)

    @api_component
    async def get_tracked_anime_episode_details(self, tracked_anime_id: int,
                                                episode_number: int,
                                                force_freshness: bool) -> TrackedAnimeItemEpisodeDetails:
        tracked_anime = await self._tracked_anime_component.get_tracked_anime_by_id(tracked_anime_id)
        if tracked_anime is None:
            raise ObjectNotFoundException(f"Tracked anime not found: {tracked_anime_id}")
        anime = await self._anilist_component.get_anime(anilist_anime_id=tracked_anime.anilist_id,
                                                        force_refresh=force_freshness,)
        episodes = await self._build_episodes(tracked_anime=tracked_anime, anime=anime,
                                              force_freshness=force_freshness,
                                              lowest=episode_number, highest=episode_number,
                                              single_episode=True)  # this flag bypasses range enforcement
        if not episodes:
            raise ObjectNotFoundException(f"Episode not found: {episode_number}")
        episode_details = episodes[0]
        episode_db_objects = [episode for episode in tracked_anime.episodes
                              if episode.episode_number == episode_number]
        episode_torrents = episode_db_objects[0].torrents if episode_db_objects else []
        torrent_items, qbit_items = [], []
        magnet_hash_torrents_map = defaultdict(list)
        for episode_torrent in episode_torrents:
            magnet_hash_torrents_map[episode_torrent.magnet_hash].append(episode_torrent)
        try:
            qbit_items = await self._qbit_component.get_torrents(magnet_hashes=magnet_hash_torrents_map.keys())
        except QbitNotConfiguredException:
            pass
        except Exception as e:
            self.logger.exception(e)
        finally:
            qbit_hash_qbit_item_map = {qbit_item.hash: qbit_item for qbit_item in qbit_items}
        for magnet_hash, torrents_ in magnet_hash_torrents_map.items():
            parent: Torrent = [torrent for torrent in torrents_ if not torrent.parent_torrent_id][0]
            children = [torrent for torrent in torrents_ if torrent.parent_torrent_id == parent.id]
            nyaa_torrent = NyaaItem.from_xml_string(parent.rss_xml)
            raw_torrent = TrackedAnimeItemEpisodeDetails.EpisodeTorrentItem.RawTorrent(
                title=nyaa_torrent.title,
                size=nyaa_torrent.size_str,
                description=nyaa_torrent.clean_description,
                web_link=nyaa_torrent.web_link,
                release_group=parent.release_group,
                anime_title=parent.title,
                episode_number=parent.episode_number,
                version_number=parent.version_number,
                language_code=parent.language_code,
                repack_indicator=parent.repack_indicator,
                resolution=parent.resolution,
                source=parent.source,
                encoding=parent.encoding,
            )
            qbit_download = qbit_hash_qbit_item_map.get(magnet_hash)
            download = TrackedAnimeItemEpisodeDetails.EpisodeTorrentItem.Download(
                id=parent.effective_download.id,
                status=parent.effective_download.status,
                status_details=parent.effective_download.status_details,
                download_directory_path=parent.effective_download.download_directory_path,
                destination_path=parent.effective_download.destination_path,
                copied_to_destination_path_at=parent.effective_download.copied_to_destination_path_at,
                qbit_status=qbit_download.state if qbit_download else None,
                qbit_progress=qbit_download.progress if qbit_download else None,
                qbit_eta=qbit_download.eta if qbit_download else None,
            ) if parent.effective_download else None
            torrent_items.append(
                TrackedAnimeItemEpisodeDetails.EpisodeTorrentItem(
                    parent_id=parent.id,
                    children_ids=[child.id for child in children],
                    raw_torrent=raw_torrent,
                    download=download,
                    effective_date=(parent.effective_download.copied_to_destination_path_at
                                    or parent.effective_download.created_at)
                    if parent.effective_download else parent.created_at
                )
            )
            torrent_items.sort(key=lambda x: x.effective_date, reverse=True)

        return TrackedAnimeItemEpisodeDetails(**episode_details.model_dump(), torrents=torrent_items)

    @api_component
    async def update_tracked_anime_episode(self, tracked_anime_id: int,
                                           episode_number: int,
                                           data: TrackedAnimeEpisodeUpdateRequest):
        await self._tracked_anime_episode_component.update_tracked_anime_episode(
            tracked_anime_id=tracked_anime_id,
            episode_number=episode_number,
            auto_discard=data.auto_discard
        )

    async def _hydrate_single(self, anime: AnilistAnime,
                              force_freshness: bool = False
                              ) -> tuple[list[AnilistAiringScheduleItem], AnilistUserListEntry | None]:
        airing_map = await self._anilist_airing_schedule_component.get_future_anime_schedule_records_map(
            anilist_id_status_map={anime.id: anime.status}, force_fetch=force_freshness
        )
        user_entry = await self._anilist_list_component.get_user_anime_list_entry(anilist_id=anime.id,
                                                                                  force_fetch=force_freshness) \
            if config.user_settings.anilist_user_token else None
        return airing_map.get(anime.id) or [], user_entry

    def _to_item(self,
                 tracked_anime: TrackedAnime,
                 anime: AnilistAnime,
                 user_entry: AnilistUserListEntry | None,
                 airing_schedule: list[AnilistAiringScheduleItem],
                 tvdb_series_id: int | None) -> TrackedAnimeItem:
        processing = tracked_anime.processing_settings
        profile = tracked_anime.profile
        episode_stats = self._get_episode_stats(tracked_anime=tracked_anime,
                                                anime=anime,
                                                airing_schedule=airing_schedule)
        return TrackedAnimeItem(
            id=tracked_anime.id,
            status=tracked_anime.status,
            anilist_id=tracked_anime.anilist_id,
            from_episode=tracked_anime.from_episode,
            show_parent_directory=tracked_anime.show_parent_directory,
            show_folder_name=tracked_anime.show_folder_name,
            episode_number_padding=processing.episode_number_padding,
            tvdb_structure_enabled=tracked_anime.tvdb_structure_enabled,
            release_profile=TrackedAnimeReleaseProfileSettings(
                id=profile.id,
                preferred_release_groups=profile.preferred_release_groups,
                preferred_encodings=profile.preferred_encodings,
                preferred_resolutions=profile.preferred_resolutions,
                preferred_language_codes=profile.preferred_language_codes,
                preferred_sources=profile.preferred_sources,
                language_codes_restricted=profile.language_codes_restricted,
                sources_restricted=profile.sources_restricted,
                accept_release_upgrades=profile.accept_release_upgrades,
                priorities_sorted=profile.priorities_sorted,
            ),
            raw_settings=TrackedAnimeRawSettings(
                raw_episode_file_name_format=processing.raw_episode_file_name_format,
            ),
            tvdb_settings=TrackedAnimeTVDBSettings(
                tvdb_season_type=tracked_anime.tvdb_season_type,
                season_number_padding=processing.season_number_padding,
                season_directory_number_padding=processing.season_directory_number_padding,
                season_directory_name_format=processing.season_directory_name_format,
                episode_file_name_format=processing.episode_file_name_format,
                titleless_episode_file_name_format=processing.titleless_episode_file_name_format,
            ),
            release_group_settings=[
                TrackedAnimeReleaseGroupSettings(
                    release_group_name=rgp.release_group,
                    episode_number_offset=rgp.episode_number_offset,
                    override_match_against=rgp.override_match_against,
                )
                for rgp in tracked_anime.release_groups_preferences
            ],
            anime=TrackedAnimeAPIComponent._to_anime_item(anime, airing_schedule, tvdb_series_id),
            user_entry=TrackedAnimeItem.UserAnimeListItem(
                progress=user_entry.progress,
                score=user_entry.score,
                status=user_entry.status,
                repeat_count=user_entry.repeat_count,
                is_private=user_entry.is_private,
                started_at=AnimeItem.AnilistDate(year=user_entry.started_at.year,
                                                 month=user_entry.started_at.month,
                                                 day=user_entry.started_at.day),
                completed_at=AnimeItem.AnilistDate(year=user_entry.completed_at.year,
                                                   month=user_entry.completed_at.month,
                                                   day=user_entry.completed_at.day),
                notes=user_entry.notes,
            ) if user_entry else None,
            episode_stats=episode_stats
        )

    @staticmethod
    def _to_anime_item(anime: AnilistAnime,
                       airing_schedule: list[AnilistAiringScheduleItem],
                       tvdb_series_id: int | None) -> AnimeItemBase:
        next_airing_episode = None
        if airing_schedule:
            soonest = sorted(airing_schedule, key=lambda x: x.airing_at)[0]
            next_airing_episode = AnilistItemAiringScheduleItem(
                airing_at=soonest.airing_at, episode=soonest.episode, anilist_id=soonest.anilist_id,
            )
        return AnimeItemBase(
            id=anime.id, idMal=anime.idMal,
            tvdb_series_id=tvdb_series_id,
            english_title=anime.english_title,
            romaji_title=anime.romaji_title,
            native_title=anime.native_title,
            season=anime.season,
            season_year=anime.season_year,
            episodes=anime.episodes,
            status=anime.status,
            average_score=anime.average_score,
            mean_score=anime.mean_score,
            next_airing_episode=next_airing_episode,
            banner_image=anime.banner_image,
            small_cover_image=anime.small_cover_image,
            medium_cover_image=anime.medium_cover_image,
            large_cover_image=anime.large_cover_image,
            format=anime.format,
            start_date=AnimeItemBase.AnilistDate(
                year=anime.start_date.year,
                month=anime.start_date.month,
                day=anime.start_date.day,
            ),
            end_date=AnimeItemBase.AnilistDate(
                year=anime.end_date.year,
                month=anime.end_date.month,
                day=anime.end_date.day,
            )
        )

    async def _build_episodes(self,
                              tracked_anime: TrackedAnime,
                              anime: AnilistAnime,
                              force_freshness: bool,
                              lowest: int | None = None,
                              highest: int | None = None,
                              single_episode: bool = False) -> list[TrackedAnimeItemEpisode]:
        freshness = timedelta(seconds=1) if force_freshness else timedelta(hours=12)
        tvdb_cache: dict[tuple[int, TVDBSeasonType], dict] = {}

        async def tvdb_episodes(series_id_: int, season_type: TVDBSeasonType) -> dict:
            key = (series_id_, season_type)
            if key not in tvdb_cache:
                series_episodes = await self._tvdb_component.get_series_episodes(
                    series_id=series_id_, season_type=season_type, minimum_freshness=freshness
                )
                tvdb_cache[key] = {ep.id: ep for ep in series_episodes.episodes}
            return tvdb_cache[key]

        existing_episode_number_to_db_record_map = {ep.episode_number: ep for ep in tracked_anime.episodes}

        latest = max(await self._determine_latest_episode(anime, tvdb_episodes) or 0,
                     max(existing_episode_number_to_db_record_map.keys() or [0])) or None
        explicit_range = highest is not None
        highest_known_episode_number = latest
        if highest is None:  # for get tracked-anime/id API
            if latest is None:
                return []
            highest = latest + 3
        if anime.episodes is not None:
            highest = min(highest, anime.episodes)
            highest_known_episode_number = anime.episodes
        if lowest is None:  # for get tracked-anime/id API
            lowest = max(highest - 25, min(tracked_anime.from_episode, highest - 1))
        lowest = max(1, lowest)

        episodes = []
        for episode_number in range(lowest, highest + 1):
            mappings = await anime_relations.get_anilist_episode_tvdb_mappings(
                anilist_id=tracked_anime.anilist_id, episode_number=episode_number
            )
            series_episode_models = []
            if mappings:
                series_id = mappings[0].series_id
                official = await tvdb_episodes(series_id, TVDBSeasonType.OFFICIAL)
                matched_ids = []
                for mapping in mappings:
                    for ep in official.values():
                        if ep.season_number == mapping.season_number and ep.number == mapping.episode_number:
                            matched_ids.append(ep.id)
                            break
                if tracked_anime.tvdb_season_type == TVDBSeasonType.OFFICIAL:
                    source = official
                else:
                    source = await tvdb_episodes(series_id, tracked_anime.tvdb_season_type)
                series_episode_models = [self._tvdb_episode_to_schema(source[ep_id])
                                         for ep_id in matched_ids if ep_id in source]

            db_record = existing_episode_number_to_db_record_map.get(episode_number)

            if not single_episode and not series_episode_models and not db_record and explicit_range:
                if highest_known_episode_number:
                    if episode_number > highest_known_episode_number:
                        continue
                else:
                    continue

            active_download = self._latest_active_download(db_record) if db_record else None
            if db_record is not None and active_download is not None:
                part = db_record.tvdb_episode_part
                part_ceiling = db_record.tvdb_episode_part_ceiling
            else:
                part = mappings[0].part if mappings else None
                part_ceiling = mappings[0].part_ceiling if mappings else None
            episodes.append(TrackedAnimeItemEpisode(
                episode_number=episode_number,
                tvdb_series_episodes=series_episode_models,
                tvdb_episode_part=part,
                tvdb_episode_part_ceiling=part_ceiling,
                auto_discard=db_record.auto_discard if db_record is not None else False,
                download_id=active_download.id if active_download else None,
                download_status=active_download.status if active_download else None,
            ))
        return episodes

    # noinspection PyMethodMayBeStatic
    async def _determine_latest_episode(self, anime: AnilistAnime, tvdb_episodes) -> int:
        if anime.next_airing_episode and anime.next_airing_episode.episode:
            return max(1, anime.next_airing_episode.episode - 1)
        if anime.episodes:
            return anime.episodes
        mappings = await anime_relations.get_anilist_episode_tvdb_mappings(anilist_id=anime.id,
                                                                           episode_number=1)
        if not mappings:
            return 1
        try:
            official = await tvdb_episodes(mappings[0].series_id, TVDBSeasonType.OFFICIAL)
        except Exception:
            return 1
        season = mappings[0].season_number
        now = datetime.now(UTC)
        tvdb_sourced_anilist_episode_numbers = [
            anilist_mapping.episode_number
            for ep in official.values()
            for anilist_mapping in await anime_relations.get_tvdb_episode_anilist_mappings(
                series_id=ep.series_id, season_number=ep.season_number, episode_number=ep.number
            )
            if ep.season_number == season != 0 and ep.air_date is not None and ep.air_date.replace(tzinfo=UTC) <= now
        ]
        return max(tvdb_sourced_anilist_episode_numbers or [1])

    @staticmethod
    def _latest_active_download(record: TrackedAnimeEpisode):
        downloads = [torrent.effective_download for torrent in record.torrents
                     if torrent.effective_download is not None
                     and torrent.effective_download.status not in (TorrentDownloadStatus.DELETED,
                                                                   TorrentDownloadStatus.DISCARDED)]
        if not downloads:
            return None
        return sorted(downloads, key=lambda d: d.copied_to_destination_path_at or d.created_at, reverse=True)[0]

    @staticmethod
    def _tvdb_episode_to_schema(
            ep) -> TrackedAnimeItemEpisode.TVDBSeriesEpisode:
        return TrackedAnimeItemEpisode.TVDBSeriesEpisode(
            id=ep.id, series_id=ep.series_id, title=ep.title, air_date=ep.air_date,
            runtime=ep.runtime, overview=ep.overview, image_url=ep.image_url, number=ep.number,
            absolute_number=ep.absolute_number, season_number=ep.season_number,
            season_name=ep.season_name, finale_type=ep.finale_type,
        )

    @staticmethod
    def _get_episode_stats(tracked_anime: TrackedAnime,
                           anime: AnilistAnime,
                           airing_schedule: list[AnilistAiringScheduleItem]) -> TrackedAnimeItem.EpisodeStats:
        next_episode = min(schedule_item.episode for schedule_item in airing_schedule) if airing_schedule else None
        if anime.status == AnilistAnimeStatus.FINISHED \
                or (not airing_schedule and anime.end_date and anime.end_date.parsed_date()
                    and (anime.end_date.parsed_date() - timedelta(hours=8)).date() <= datetime.now(UTC).date()):
            latest_known_episode_number = anime.episodes
        elif next_episode:
            latest_known_episode_number = next_episode - 1
        elif anime.status == AnilistAnimeStatus.NOT_YET_RELEASED:
            latest_known_episode_number = 0
        else:
            latest_known_episode_number = None

        processed_episode_count = downloading_episode_count = failed_episode_count = 0
        for episode in tracked_anime.episodes:
            if episode.episode_number < tracked_anime.from_episode or \
                    (latest_known_episode_number and episode.episode_number > latest_known_episode_number):
                continue
            for torrent in episode.torrents:
                if torrent.effective_download is None:
                    continue
                if torrent.effective_download.status == TorrentDownloadStatus.PROCESSED:
                    processed_episode_count += 1
                    break
                elif torrent.effective_download.status in [TorrentDownloadStatus.PROCESSING,
                                                           TorrentDownloadStatus.DOWNLOADED,
                                                           TorrentDownloadStatus.DOWNLOADING,
                                                           TorrentDownloadStatus.PENDING]:
                    downloading_episode_count += 1
                    break
                elif torrent.effective_download.status in [TorrentDownloadStatus.FAILED_PROCESSING,
                                                           TorrentDownloadStatus.FAILED_DOWNLOAD,
                                                           TorrentDownloadStatus.FAILED_DOWNLOAD_INIT]:
                    failed_episode_count += 1
                    break

        return TrackedAnimeItem.EpisodeStats(
            latest_known_episode_number=latest_known_episode_number,
            processed_episode_count=processed_episode_count,
            downloading_episode_count=downloading_episode_count,
            failed_episode_count=failed_episode_count
        )
