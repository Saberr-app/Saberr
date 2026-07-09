from api.schemas.anime_schemas import AnimeListRequest
from api.schemas.search_schema import SearchRequest, SearchResponse, SearchTVDBResponse
from common.db import get_session
from common.decorators import api_component
from components import BaseComponent
from components.operational_components.tracked_anime_component import TrackedAnimeComponent
from components.service_components.anilist_component import AnilistComponent
from components.service_components.anilist_list_component import AnilistListComponent
from components.service_components.tvdb_component import TVDBComponent
from config import config
from constants import AnilistAnimeUserStatus, TrackedAnimeStatus
from dto.anilist import AnilistAnime
from repositories.cache_repositories.anilist_anime_repo import AnilistAnimeRepo


class SearchAPIComponent(BaseComponent):
    PAGE_SIZE = 5

    def __init__(self):
        super().__init__()
        self._anilist_component = AnilistComponent()
        self._anilist_list_component = AnilistListComponent()
        self._tracked_anime_component = TrackedAnimeComponent()
        self._tvdb_component = TVDBComponent()

    @api_component
    async def search(self, body: SearchRequest) -> SearchResponse:
        if len(body.query.strip()) < 3:
            return SearchResponse(anime=[])
        anilist_anime_list = await AnilistAnimeRepo(get_session()).search_anime(search_query=body.query)
        anilist_anime_items = AnilistAnime.many_from_dict([anilist_anime.data
                                                           for anilist_anime
                                                           in anilist_anime_list])
        if len(anilist_anime_list) < self.PAGE_SIZE:
            anilist_search_results = await self._anilist_component.get_anime_with_filters(
                query=body.query,
                per_page=self.PAGE_SIZE,
                sort=[AnimeListRequest.AnimeSortBy.SEARCH_MATCH.value],
            )
            anilist_anime_items = anilist_search_results + [
                anilist_anime for anilist_anime in anilist_anime_items if anilist_anime.id not in {
                    search_result.id for search_result in anilist_search_results
                }
            ]
        tracked_anime_list = await self._tracked_anime_component.get_tracked_anime_by_anilist_ids(
            anilist_ids=[anilist_anime.id for anilist_anime in anilist_anime_items],
            load_relations=False
        )
        anilist_id_tracked_anime_map = {tracked_anime.anilist_id: tracked_anime
                                        for tracked_anime in tracked_anime_list
                                        if tracked_anime.status == TrackedAnimeStatus.ACTIVE}
        user_list_entries = await self._anilist_list_component.get_user_anime_list_entries(
            anilist_ids=[anilist_anime.id for anilist_anime in anilist_anime_items]
        ) if config.user_settings.anilist_user_token else []
        anilist_id_user_list_map = {user_list_entry.anime_id: user_list_entry
                                    for user_list_entry in user_list_entries}
        anime_items = []
        for anilist_anime in anilist_anime_items:
            tracked_anime = anilist_id_tracked_anime_map.get(anilist_anime.id)
            user_list_entry = anilist_id_user_list_map.get(anilist_anime.id)
            anime_items.append(SearchResponse.AnimeResult(
                anilist_id=anilist_anime.id,
                romaji_title=anilist_anime.romaji_title,
                english_title=anilist_anime.english_title,
                native_title=anilist_anime.native_title,
                episodes=anilist_anime.episodes,
                format=anilist_anime.format,
                season=anilist_anime.season,
                season_year=anilist_anime.season_year,
                status=anilist_anime.status,
                small_cover_image=anilist_anime.small_cover_image,
                user_list_status=user_list_entry.status if user_list_entry else None,
                tracked_anime_id=tracked_anime.id if tracked_anime else None
            ))
        anime_items.sort(
            key=lambda item: (item.tracked_anime_id is not None,
                              {AnilistAnimeUserStatus.CURRENT: 4,
                               AnilistAnimeUserStatus.REPEATING: 3,
                               AnilistAnimeUserStatus.PLANNING: 2,
                               AnilistAnimeUserStatus.COMPLETED: 1}.get(item.user_list_status, 0)),
            reverse=True
        )
        return SearchResponse(anime=anime_items[:self.PAGE_SIZE])

    @api_component
    async def search_tvdb(self, body) -> SearchTVDBResponse:
        if len(body.query.strip()) < 3:
            return SearchTVDBResponse(tvdb_series=[])
        search_results = await self._tvdb_component.search_series(name=body.query)
        return SearchTVDBResponse(tvdb_series=[
            SearchTVDBResponse.TVDBSeriesResult(
                id=search_result.id,
                title=search_result.english_name or search_result.original_name,
                year=search_result.year,
                image_url=search_result.image_url,
                status=search_result.status,
            ) for search_result in search_results
        ])
