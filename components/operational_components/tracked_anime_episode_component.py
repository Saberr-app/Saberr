from datetime import timedelta

from app_state import anime_relations
from common.db import get_session
from common.exceptions import TVDBIncompleteDataException
from components.operational_components import BaseOperationalComponent
from components.service_components.tvdb_component import TVDBComponent
from constants import TVDBSeasonType
from dto.orm_models import TrackedAnimeEpisode, TrackedAnime
from dto.tvdb import AnilistEpisodeTVDBMapping
from system import UNSET
from repositories.tracked_anime_repositories.tracked_anime_episode_repo import TrackedAnimeEpisodeRepo
from repositories.tracked_anime_repositories.tracked_anime_repo import TrackedAnimeRepo


class TrackedAnimeEpisodeComponent(BaseOperationalComponent):

    def __init__(self):
        super().__init__()
        self._tvdb_component = TVDBComponent()

    async def get_or_create_tracked_anime_episode(self,
                                                  episode_number: int,
                                                  tracked_anime_id: int | None = None,
                                                  tracked_anime: TrackedAnime | None = None,
                                                  set_auto_discard_to: bool = UNSET,
                                                  tvdb_data_freshness_minimum: timedelta | None = None,
                                                  raise_on_tvdb_unavailability: bool = False) -> TrackedAnimeEpisode:
        if tracked_anime_id is None and tracked_anime is None:
            raise ValueError("Either tracked_anime_id or tracked_anime must be provided")
        if tracked_anime is None:
            tracked_anime = await TrackedAnimeRepo(get_session()).get_tracked_anime(tracked_anime_id=tracked_anime_id,
                                                                                    load_relations=False)
        tvdb_mappings = await anime_relations.get_anilist_episode_tvdb_mappings(anilist_id=tracked_anime.anilist_id,
                                                                                episode_number=episode_number)
        await self._populate_episode_tvdb_mappings_data(tvdb_mappings=tvdb_mappings,
                                                        raise_on_tvdb_unavailability=raise_on_tvdb_unavailability,
                                                        minimum_freshness=tvdb_data_freshness_minimum)
        overrides = {}
        if set_auto_discard_to is not UNSET:
            overrides["auto_discard"] = set_auto_discard_to
        if not (episode := await TrackedAnimeEpisodeRepo(get_session()).get_tracked_anime_episode(
                tracked_anime_id=tracked_anime.id,
                episode_number=episode_number
        )):
            episode = await TrackedAnimeEpisodeRepo(get_session()).create_tracked_anime_episode(
                tracked_anime_id=tracked_anime.id,
                episode_number=episode_number,
                tvdb_series_id=tvdb_mappings[0].series_id if tvdb_mappings else None,
                tvdb_season_number=tvdb_mappings[0].season_number if tvdb_mappings else None,
                tvdb_episode_numbers=[mapping.episode_number for mapping in tvdb_mappings],
                tvdb_episode_ids=[mapping.episode_id for mapping in tvdb_mappings],
                tvdb_episode_part=tvdb_mappings[0].part if tvdb_mappings else None,
                tvdb_episode_part_ceiling=tvdb_mappings[0].part_ceiling if tvdb_mappings else None,
                **overrides
            )
        else:
            await TrackedAnimeEpisodeRepo(get_session()).update_tracked_anime_episode(
                tracked_anime_episode_id=episode.id,
                tvdb_series_id=tvdb_mappings[0].series_id if tvdb_mappings else None,
                tvdb_season_number=tvdb_mappings[0].season_number if tvdb_mappings else None,
                tvdb_episode_numbers=[mapping.episode_number for mapping in tvdb_mappings],
                tvdb_episode_ids=[mapping.episode_id for mapping in tvdb_mappings],
                tvdb_episode_part=tvdb_mappings[0].part if tvdb_mappings else None,
                tvdb_episode_part_ceiling=tvdb_mappings[0].part_ceiling if tvdb_mappings else None,
                **overrides
            )
        return episode

    async def update_tracked_anime_episode(self, tracked_anime_id: int,
                                           episode_number: int,
                                           auto_discard: bool = UNSET):
        if auto_discard is UNSET:
            return
        await self.get_or_create_tracked_anime_episode(tracked_anime_id=tracked_anime_id,
                                                       episode_number=episode_number,
                                                       set_auto_discard_to=auto_discard)

    async def _populate_episode_tvdb_mappings_data(self, tvdb_mappings: list[AnilistEpisodeTVDBMapping],
                                                   minimum_freshness: timedelta | None = None,
                                                   raise_on_tvdb_unavailability: bool = False,):
        if not tvdb_mappings:
            return
        try:
            tvdb_episodes = await self._tvdb_component.get_series_episodes(
                series_id=tvdb_mappings[0].series_id,
                season_type=TVDBSeasonType.OFFICIAL,
                minimum_freshness=minimum_freshness
            )
        except Exception as e:
            if raise_on_tvdb_unavailability:
                raise TVDBIncompleteDataException(f"Failed to fetch TVDB episodes for "
                                                  f"populating episode mappings data: {e}")
            self.logger.debug(f"Failed to fetch TVDB episodes for populating episode mappings data: "
                              f"(tvdb_id={tvdb_mappings[0].series_id}) {e}")
            return
        season_episode_mapping_map: dict[tuple, AnilistEpisodeTVDBMapping] = {
            (mapping.season_number, mapping.episode_number): mapping
            for mapping in tvdb_mappings
        }
        for episode in tvdb_episodes.episodes:
            key = (episode.season_number, episode.number)
            if key in season_episode_mapping_map:
                mapping = season_episode_mapping_map[key]
                mapping.episode_id = episode.id
                season_episode_mapping_map.pop(key)

        if season_episode_mapping_map:
            if raise_on_tvdb_unavailability:
                raise TVDBIncompleteDataException(f"Failed to find all required TVDB episodes for "
                                                  f"populating episode mappings data")
            else:
                self.logger.debug(f"Failed to find all required TVDB episodes for "
                                  f"populating episode mappings data: {season_episode_mapping_map.keys()}")
