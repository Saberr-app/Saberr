from datetime import timedelta
from pathlib import Path
from typing import Iterable

from app_state import anime_relations
from components.operational_components import BaseOperationalComponent
from components.service_components.anilist_component import AnilistComponent
from system import UNSET
from common.db import get_session
from common.exceptions import AnilistRelationsEpisodeCountMismatch, ExternalServiceException
from config import config
from constants import TrackedAnimeStatus, ReleaseCriteriaProperty
from dto.anilist import AnilistAnimeMinimal
from dto.nyaa_item import NyaaItem, RawTorrent
from dto.orm_models import Torrent, TrackedAnimeProfile, TorrentDownload, TrackedAnimeReleaseGroupPreferences
from repositories.torrent_repositories.torrent_repo import TorrentRepo
from utils.helpers.text_helpers import clean_path_name
from utils.recognition_utils import get_matched_release_group_in_torrent_title, extract_release_title_parts_from_torrent


class TorrentComponent(BaseOperationalComponent):

    def __init__(self):
        from components.operational_components.tracked_anime_component import TrackedAnimeComponent
        from components.operational_components.tracked_anime_episode_component import TrackedAnimeEpisodeComponent
        from components.operational_components.torrent_download_component import TorrentDownloadComponent
        super().__init__()
        self._tracked_anime_component = TrackedAnimeComponent()
        self._anilist_component = AnilistComponent()
        self._tracked_anime_episode_component = TrackedAnimeEpisodeComponent()
        self._torrent_download_component = TorrentDownloadComponent()

    # noinspection PyMethodMayBeStatic
    async def get_torrents_by_hashes(self, magnet_hashes: Iterable[str],
                                     exclude_discarded: bool = False,
                                     parent_torrent_only: bool = False) -> list[Torrent]:
        return await TorrentRepo(get_session()).get_torrents_by_hashes(
            magnet_hashes=magnet_hashes,
            discarded=False if exclude_discarded else None,
            parent_torrent_id=None if parent_torrent_only else UNSET,
            load_relations=True
        )

    @staticmethod
    def init_raw_torrent(nyaa_item: NyaaItem) -> RawTorrent:
        raw_torrent = RawTorrent(
            nyaa_item=nyaa_item,
            title_parts=None,
            release_group_settings=None,
            anilist_anime_min=None,
            anilist_episode_number=None
        )
        release_group = get_matched_release_group_in_torrent_title(torrent_title=nyaa_item.title,
                                                                   release_groups_map=config.release_groups_map)
        if not release_group:
            raw_torrent.add_note("No matching release group found in torrent title.", error=True)
            return raw_torrent
        raw_torrent.release_group_settings = release_group
        if release_group.batch_keyword in nyaa_item.title:
            raw_torrent.is_batch_torrent = True
        torrent_title_parts = extract_release_title_parts_from_torrent(torrent_title=nyaa_item.title,
                                                                       release_group_settings=release_group)
        if not torrent_title_parts:
            raw_torrent.add_note("Could not parse all required details from the torrent title.", error=True)
            return raw_torrent
        torrent_title_parts.is_batch = raw_torrent.is_batch_torrent
        raw_torrent.title_parts = torrent_title_parts
        return raw_torrent

    async def populate_raw_torrents_data(self, raw_torrents: list[RawTorrent]) -> None:
        db_torrents = await self.get_torrents_by_hashes(
            magnet_hashes={raw_torrent.nyaa_item.magnet_hash for raw_torrent in raw_torrents}
        )
        anilist_queries = [
            title for raw_torrent in raw_torrents for title in (raw_torrent.title_parts.title,
                                                                raw_torrent.title_parts.search_title)
        ]
        title_result_map = await self._anilist_component.get_anime_multi_search_results(queries=anilist_queries)

        hash_db_torrents_map = {}
        for db_torrent in db_torrents:
            if db_torrent.magnet_hash not in hash_db_torrents_map:
                hash_db_torrents_map[db_torrent.magnet_hash] = []
            hash_db_torrents_map[db_torrent.magnet_hash].append(db_torrent)

        to_preprocess_raw_torrents_tuples = []
        hash_parent_db_torrent_map = {}
        for raw_torrent in raw_torrents:
            nyaa_item = raw_torrent.nyaa_item
            anilist_anime = title_result_map.get(raw_torrent.title_parts.search_title) \
                or title_result_map.get(raw_torrent.title_parts.title)
            if nyaa_item.magnet_hash in hash_db_torrents_map:
                parent_db_torrent, other_db_torrents = None, []
                for db_torrent in hash_db_torrents_map[nyaa_item.magnet_hash]:
                    if not db_torrent.parent_torrent_id:
                        parent_db_torrent = db_torrent
                    else:
                        other_db_torrents.append(db_torrent)
                if not parent_db_torrent:
                    raw_torrent.add_note("Database inconsistency: torrent exists without a parent.", error=True)
                    continue
                if parent_db_torrent.has_active_download():
                    # if processed
                    await self._populate_processed_raw_torrent(raw_torrent, parent_db_torrent, other_db_torrents)
                else:
                    # only send parent_db_torrent since the only way there could be multiple torrents per hash
                    #  is through identifying into processing, which is handled in the previous if case
                    to_preprocess_raw_torrents_tuples.append((raw_torrent, anilist_anime))
                    hash_parent_db_torrent_map[nyaa_item.magnet_hash] = parent_db_torrent
            else:
                to_preprocess_raw_torrents_tuples.append((raw_torrent, anilist_anime))

        overrides_map = await self._tracked_anime_component.get_tracked_anime_release_group_overrides_map(
            title_release_group_pairs={
                (raw_torrent.title_parts.search_title, raw_torrent.title_parts.release_group)
                for raw_torrent, _ in to_preprocess_raw_torrents_tuples
            }
        )
        for raw_torrent, anilist_anime in to_preprocess_raw_torrents_tuples:
            await self._preprocess_raw_torrent(
                raw_torrent=raw_torrent,
                anilist_anime_min=anilist_anime,
                overriding_release_groups_preferences=overrides_map.get(
                    (raw_torrent.title_parts.search_title,
                     raw_torrent.title_parts.release_group))
            )
        await self._process_raw_torrents(
            raw_torrents=[raw_torrent for raw_torrent, _ in to_preprocess_raw_torrents_tuples
                          if raw_torrent.t_to_process],
            hash_parent_db_torrent_map=hash_parent_db_torrent_map
        )

    # noinspection PyMethodMayBeStatic
    async def _populate_processed_raw_torrent(self,
                                              raw_torrent: RawTorrent,
                                              db_torrent: Torrent,
                                              other_db_torrents: list[Torrent]):
        raw_torrent.db_episode_id = db_torrent.tracked_anime_episode.id
        raw_torrent.other_db_episode_ids = [db_torrent.tracked_anime_episode.id for db_torrent in other_db_torrents]
        raw_torrent.db_torrent_id = db_torrent.id
        raw_torrent.other_episodes_db_torrent_ids = [db_torrent.id for db_torrent in other_db_torrents]
        raw_torrent.db_download_id = db_torrent.effective_download.id

        raw_torrent.anilist_episode_number = db_torrent.tracked_anime_episode.episode_number
        raw_torrent.episode_part = db_torrent.episode_part
        raw_torrent.episode_part_ceiling = db_torrent.episode_part_ceiling
        raw_torrent.anilist_anime_min = AnilistAnimeMinimal.from_tracked_anime(
            db_torrent.tracked_anime_episode.tracked_anime
        )

    # noinspection PyMethodMayBeStatic
    async def _preprocess_raw_torrent(
            self,
            raw_torrent: RawTorrent,
            anilist_anime_min: AnilistAnimeMinimal,
            overriding_release_groups_preferences: TrackedAnimeReleaseGroupPreferences | None
    ):
        raw_torrent.anilist_episode_number = raw_torrent.title_parts.episode_number
        overriding_tracked_anime = overriding_release_groups_preferences.tracked_anime \
            if overriding_release_groups_preferences else None

        if not anilist_anime_min:
            if overriding_tracked_anime:
                raw_torrent.add_note("Torrent title did not yield Anilist search results, but "
                                     "a tracked anime was matched based on title and release group preferences.")
                if overriding_release_groups_preferences.episode_number_offset >= raw_torrent.anilist_episode_number:
                    raw_torrent.require_identifying_data_on_override = True
                    raw_torrent.add_note("Release group preferences episode number offset is greater than or equal to "
                                         "the episode number parsed from the torrent title, cannot apply offset.",
                                         error=True)
                    return
                raw_torrent.anilist_anime_min = AnilistAnimeMinimal.from_tracked_anime(overriding_tracked_anime)
                raw_torrent.anilist_episode_number -= overriding_release_groups_preferences.episode_number_offset
                raw_torrent.t_tracked_anilist_id = overriding_tracked_anime.anilist_id
            else:
                raw_torrent.require_identifying_data_on_override = True
                raw_torrent.add_note("Failed to match torrent title to an anime on Anilist.", error=True)
                return
        else:
            if overriding_tracked_anime and overriding_tracked_anime.status == TrackedAnimeStatus.ACTIVE \
                    and overriding_release_groups_preferences.episode_number_offset \
                    < raw_torrent.anilist_episode_number:
                raw_torrent.add_note("Torrent match overridden based on release group preferences.")
                raw_torrent.anilist_anime_min = AnilistAnimeMinimal.from_tracked_anime(overriding_tracked_anime)
                raw_torrent.anilist_episode_number -= overriding_release_groups_preferences.episode_number_offset
                raw_torrent.t_tracked_anilist_id = overriding_tracked_anime.anilist_id
            else:
                try:
                    anilist_id, raw_torrent.anilist_episode_number = await anime_relations.resolve_anime(
                        original_anilist_id=anilist_anime_min.id,
                        original_episode_number=raw_torrent.anilist_episode_number
                    )
                except AnilistRelationsEpisodeCountMismatch as e:
                    raw_torrent.require_identifying_data_on_override = True
                    raw_torrent.add_note(e.detail, error=True)
                    return
                if anilist_id != anilist_anime_min.id:
                    raw_torrent.t_relations_anilist_id = anilist_id
                else:
                    raw_torrent.anilist_anime_min = anilist_anime_min

        raw_torrent.t_to_process = True

    async def _process_raw_torrents(self, raw_torrents, hash_parent_db_torrent_map):
        relevant_anilist_ids = {raw_torrent.t_relations_anilist_id for raw_torrent in raw_torrents
                                if raw_torrent.t_relations_anilist_id}
        relevant_anilist_ids |= {raw_torrent.t_tracked_anilist_id for raw_torrent in raw_torrents
                                 if raw_torrent.t_tracked_anilist_id}
        relevant_anilist_ids |= {raw_torrent.anilist_anime_min.id for raw_torrent in raw_torrents
                                 if raw_torrent.anilist_anime_min}
        tracked_anime_list = await self._tracked_anime_component.get_tracked_anime_by_anilist_ids(
            anilist_ids=relevant_anilist_ids,
            load_relations=False
        )
        anilist_id_tracked_anime_map = {tracked_anime.anilist_id: tracked_anime for tracked_anime in tracked_anime_list}
        try:
            overriding_anilist_anime = await self._anilist_component.get_anime_records(
                anilist_anime_ids={raw_torrent.t_relations_anilist_id for raw_torrent in raw_torrents
                                   if raw_torrent.t_relations_anilist_id}
            )
        except ExternalServiceException as e:
            self.logger.warning(f"Failed to retrieve anime details from Anilist while processing raw torrents: {e}")
            overriding_anilist_anime = []
        overriding_anilist_id_anilist_anime_map = {anilist_anime.id: anilist_anime
                                                   for anilist_anime in overriding_anilist_anime}
        raw_torrents_ = []
        for raw_torrent in raw_torrents:
            if relations_override_anilist_anime := overriding_anilist_id_anilist_anime_map.get(
                    raw_torrent.t_relations_anilist_id
            ):
                raw_torrent.add_note("Torrent match overridden based on Taiga's anime relations.")
                raw_torrent.anilist_anime_min = AnilistAnimeMinimal.from_anilist_anime(relations_override_anilist_anime)
            elif raw_torrent.t_relations_anilist_id:
                raw_torrent.require_identifying_data_on_override = True
                raw_torrent.add_note("Failed to retrieve anime details from Anilist.", error=True)
                continue
            tracked_anime = anilist_id_tracked_anime_map.get(raw_torrent.anilist_anime_min.id)
            if not tracked_anime:
                raw_torrent.require_identifying_data_on_override = True
                raw_torrent.not_tracked = True
                raw_torrent.add_note(f"Anime not tracked.")
                continue
            elif tracked_anime.status != TrackedAnimeStatus.ACTIVE:
                raw_torrent.not_tracked = True
                raw_torrent.add_note(f"Anime not tracked.")
                continue
            elif raw_torrent.anilist_episode_number < tracked_anime.from_episode:
                raw_torrent.not_tracked = True
                raw_torrent.add_note(f"Episode number {raw_torrent.anilist_episode_number} not in tracked range "
                                     f"({tracked_anime.from_episode}-).")
                continue
            raw_torrents_.append(raw_torrent)
        anilist_id_episode_number_tuples = {
            (raw_torrent.anilist_anime_min.id, raw_torrent.anilist_episode_number) for raw_torrent in raw_torrents_
        }
        anilist_id_episode_number_tracked_anime_episode_map = {}
        for anilist_id, episode_number in anilist_id_episode_number_tuples:
            anilist_id_episode_number_tracked_anime_episode_map[(anilist_id, episode_number)] = \
                await self._tracked_anime_episode_component.get_or_create_tracked_anime_episode(
                    tracked_anime=anilist_id_tracked_anime_map[anilist_id],
                    episode_number=episode_number,
                    tvdb_data_freshness_minimum=timedelta(hours=12)
                )
        torrent_repo = TorrentRepo(get_session())
        db_torrent_update_data = []
        for raw_torrent in raw_torrents_:
            tracked_anime_episode = anilist_id_episode_number_tracked_anime_episode_map[
                (raw_torrent.anilist_anime_min.id, raw_torrent.anilist_episode_number)
            ]
            db_torrent = hash_parent_db_torrent_map.get(raw_torrent.nyaa_item.magnet_hash)
            raw_torrent.discarded = tracked_anime_episode.auto_discard or (db_torrent.discarded
                                                                           if db_torrent else False)
            release_group = config.release_groups_map[raw_torrent.title_parts.release_group]
            if db_torrent:
                db_torrent_update_data.append(
                    dict(
                        id=db_torrent.id,
                        magnet_hash=raw_torrent.nyaa_item.magnet_hash,
                        tracked_anime_episode_id=tracked_anime_episode.id,
                        rss_xml=raw_torrent.nyaa_item.source_xml,
                        torrent_title=raw_torrent.nyaa_item.title,
                        release_group=raw_torrent.title_parts.release_group,
                        title=raw_torrent.title_parts.title,
                        episode_number=raw_torrent.title_parts.episode_number,
                        episode_part=raw_torrent.episode_part,
                        episode_part_ceiling=raw_torrent.episode_part_ceiling,
                        language_code=raw_torrent.title_parts.language_code or release_group.default_language_code,
                        encoding=raw_torrent.title_parts.encoding or release_group.default_encoding,
                        resolution=raw_torrent.title_parts.resolution or release_group.default_resolution,
                        version_number=raw_torrent.title_parts.version_number or 1,
                        repack_indicator=raw_torrent.title_parts.repack_indicator or False,
                        source=raw_torrent.title_parts.source,
                        discarded=raw_torrent.discarded
                    )
                )
            else:
                db_torrent = await torrent_repo.create_torrent(
                    magnet_hash=raw_torrent.nyaa_item.magnet_hash,
                    tracked_anime_episode_id=tracked_anime_episode.id,
                    rss_xml=raw_torrent.nyaa_item.source_xml,
                    torrent_link=raw_torrent.nyaa_item.link,
                    torrent_title=raw_torrent.nyaa_item.title,
                    release_group=raw_torrent.title_parts.release_group,
                    title=raw_torrent.title_parts.title,
                    episode_number=raw_torrent.title_parts.episode_number,
                    episode_part=raw_torrent.episode_part,
                    episode_part_ceiling=raw_torrent.episode_part_ceiling,
                    language_code=raw_torrent.title_parts.language_code or release_group.default_language_code,
                    encoding=raw_torrent.title_parts.encoding or release_group.default_encoding,
                    resolution=raw_torrent.title_parts.resolution or release_group.default_resolution,
                    version_number=raw_torrent.title_parts.version_number,
                    repack_indicator=raw_torrent.title_parts.repack_indicator,
                    source=raw_torrent.title_parts.source,
                    parent_torrent_id=None,
                    discarded=raw_torrent.discarded,
                    override=False
                )
                # if tracked_anime_episode.auto_discard: # spammy
                #     await self._audit_log_component.log_torrent_discarded_action(
                #         db_torrent=db_torrent,
                #         tracked_anime_episode=tracked_anime_episode,
                #         tracked_anime=anilist_id_tracked_anime_map[raw_torrent.anilist_anime_min.id]
                #     )
            raw_torrent.db_episode_id = tracked_anime_episode.id
            raw_torrent.db_torrent_id = db_torrent.id
        await torrent_repo.bulk_update_torrents(data=db_torrent_update_data)

    async def determine_torrents_candidacy(self,
                                           episode_ids: Iterable[int],
                                           scope_hashes: set[str] | None
                                           ) -> tuple[set[str], dict[str, list[ReleaseCriteriaProperty]]]:
        db_torrents = await TorrentRepo(get_session()).get_torrents_by_tracked_anime_episode_ids(
            episode_ids=set(episode_ids), load_relations=True, exclude_discarded=True
        )

        db_torrent_groups = {}
        selected_hashes = set()
        dismissed_hashes_to_reasons = {}
        for db_torrent in db_torrents:
            if (scope_hashes is not None
                    and db_torrent.magnet_hash not in scope_hashes
                    and not db_torrent.has_active_download()):
                continue
            dismissal_reasons = self._validate_torrent_candidacy(
                db_torrent=db_torrent, anime_profile=db_torrent.tracked_anime_episode.tracked_anime.profile
            )
            if dismissal_reasons:
                dismissed_hashes_to_reasons[db_torrent.magnet_hash] = dismissal_reasons
                continue
            key = (db_torrent.tracked_anime_episode_id, db_torrent.episode_part, db_torrent.episode_part_ceiling)
            if key not in db_torrent_groups:
                db_torrent_groups[key] = []
            db_torrent_groups[key].append(db_torrent)

        for db_torrent_group in db_torrent_groups.values():
            anime_profile = db_torrent_group[0].tracked_anime_episode.tracked_anime.profile
            if not anime_profile.accept_release_upgrades:
                existing_downloads = [torrent for torrent in db_torrent_group if torrent.has_active_download()]
                if existing_downloads:
                    # already acquired a release for this episode/part; don't switch to a newer one
                    selected_hashes.add(sorted(torrent.magnet_hash for torrent in existing_downloads)[0])
                    continue
            best_candidate = self.get_best_torrent_for_episode(db_torrent_group, anime_profile)
            if best_candidate:
                selected_hashes.add(best_candidate.magnet_hash)
        return selected_hashes, dismissed_hashes_to_reasons

    @staticmethod
    def get_best_torrent_for_episode(db_torrents: list[Torrent],
                                     anime_profile: TrackedAnimeProfile) -> Torrent | None:
        if not db_torrents:
            return None
        if len(db_torrents) == 1:
            return db_torrents[0]

        priorities = anime_profile.priorities_sorted
        candidates = list(db_torrents)

        def preference_rank(preferences: list, candidate_value) -> int:
            normalized_preferences = [getattr(pref, "value", pref) for pref in preferences]
            normalized_value = getattr(candidate_value, "value", candidate_value)
            return normalized_preferences.index(normalized_value) \
                if normalized_value in normalized_preferences \
                else len(normalized_preferences)

        def keep_best_by_preference(preferences: list, extract_value) -> None:
            nonlocal candidates
            ranked = {}
            for torrent in candidates:
                rank = preference_rank(preferences, extract_value(torrent))
                ranked.setdefault(rank, []).append(torrent)
            best_rank = min(ranked.keys())
            candidates = ranked[best_rank]

        for priority in priorities:
            if len(candidates) <= 1:
                break
            if priority == ReleaseCriteriaProperty.VERSION:
                best_version = max([torrent.version_number for torrent in candidates])
                candidates = [torrent for torrent in candidates if torrent.version_number == best_version]
            elif priority == ReleaseCriteriaProperty.RELEASE_GROUP:
                keep_best_by_preference(anime_profile.preferred_release_groups,
                                        lambda torrent: torrent.release_group)
            elif priority == ReleaseCriteriaProperty.ENCODING:
                keep_best_by_preference(anime_profile.preferred_encodings,
                                        lambda torrent: torrent.encoding)
            elif priority == ReleaseCriteriaProperty.RESOLUTION:
                keep_best_by_preference(anime_profile.preferred_resolutions,
                                        lambda torrent: torrent.resolution)
            elif priority == ReleaseCriteriaProperty.SOURCE:
                keep_best_by_preference(anime_profile.preferred_sources,
                                        lambda torrent: torrent.source)
            elif priority == ReleaseCriteriaProperty.LANGUAGE_CODE:
                keep_best_by_preference(anime_profile.preferred_language_codes,
                                        lambda torrent: torrent.language_code)
        if candidates:
            candidates.sort(key=lambda torrent: (torrent.repack_indicator, torrent.magnet_hash), reverse=True)
            return candidates[0]
        return None

    @staticmethod
    def _validate_torrent_candidacy(db_torrent: Torrent,
                                    anime_profile: TrackedAnimeProfile) -> list[ReleaseCriteriaProperty]:
        dismissal_reasons = []
        if anime_profile.preferred_release_groups \
                and db_torrent.release_group not in anime_profile.preferred_release_groups:
            dismissal_reasons.append(ReleaseCriteriaProperty.RELEASE_GROUP)
        if anime_profile.preferred_encodings \
                and db_torrent.encoding not in anime_profile.preferred_encodings:
            dismissal_reasons.append(ReleaseCriteriaProperty.ENCODING)
        if anime_profile.preferred_resolutions \
                and db_torrent.resolution not in anime_profile.preferred_resolutions:
            dismissal_reasons.append(ReleaseCriteriaProperty.RESOLUTION)
        if anime_profile.sources_restricted and anime_profile.preferred_sources \
                and db_torrent.source not in anime_profile.preferred_sources:
            dismissal_reasons.append(ReleaseCriteriaProperty.SOURCE)
        if anime_profile.language_codes_restricted and anime_profile.preferred_language_codes \
                and db_torrent.language_code not in anime_profile.preferred_language_codes:
            dismissal_reasons.append(ReleaseCriteriaProperty.LANGUAGE_CODE)
        return dismissal_reasons

    async def select_torrent_for_downloading(self, magnet_hash: str) -> TorrentDownload:
        db_torrents = await self.get_torrents_by_hashes(
            magnet_hashes=[magnet_hash],
        )

        tracked_anime = db_torrents[0].tracked_anime_episode.tracked_anime
        download_directory_path = Path(config.user_settings.staging_directory) \
            if config.user_settings.staging_directory else None
        if download_directory_path and config.user_settings.organize_downloads:
            download_directory_path /= clean_path_name(tracked_anime.preferred_title)
        parent_db_torrent = [db_torrent for db_torrent
                             in db_torrents if db_torrent.parent_torrent_id is None][0]
        if not parent_db_torrent.effective_download:
            return await self._torrent_download_component.create_downloads_for_torrent(
                db_torrent_group=db_torrents,
                download_directory_path=str(download_directory_path) if download_directory_path else None
            )
        return parent_db_torrent.effective_download
