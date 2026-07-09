from datetime import timedelta

from app_state import anime_relations
from common.decorators import api_component
from common.exceptions import AnilistNotFoundException
from components.service_components.anilist_component import AnilistComponent
from components.service_components.anilist_list_component import AnilistListComponent
from components.operational_components.tracked_anime_component import TrackedAnimeComponent
from components.service_components.anilist_airing_schedule_component import AnilistAiringScheduleComponent
from components import BaseComponent
from components.service_components.tvdb_component import TVDBComponent
from config import config
from constants import AnilistFormat, AnilistAnimeFormat, TrackedAnimeStatus, MetadataSource
from dto.anilist import AnilistAnime, AnilistAiringScheduleItem, AnilistUserListEntry
from api.schemas.anime_schemas import AnimeListRequest, AnimeListResponse, AnimeItem, \
    AnilistItemAiringScheduleItem, AnilistMetadataResponse, AnimeItemWithUserEntry, AnimeExtras, AnimeTitlesResponse
from services.anilist_service import AnilistService


class AnimeAPIComponent(BaseComponent):

    def __init__(self):
        super().__init__()
        self._anilist_component = AnilistComponent()
        self._anilist_list_component = AnilistListComponent()
        self._anilist_service = AnilistService()
        self._tracked_anime_component = TrackedAnimeComponent()
        self._anilist_airing_schedule_component = AnilistAiringScheduleComponent()

    @api_component
    async def get_list_of_anime(self, params: AnimeListRequest) -> AnimeListResponse:
        anime_records = await self._anilist_component.get_anime_with_filters(
            query=params.query,
            statuses=params.statuses,
            season=params.season,
            season_year=params.season_year,
            formats=params.formats,
            sources=params.sources,
            genres=params.genres,
            tags=params.tags,
            exclude_genres=params.exclude_genres,
            exclude_tags=params.exclude_tags,
            on_list=params.on_list,
            page=params.page,
            sort=[sort_by.value for sort_by in params.sort_by] + [AnimeListRequest.AnimeSortBy.ID.value],
            force_fetch=params.force_freshness,
        )
        airing_schedules = await self._anilist_airing_schedule_component.get_future_anime_schedule_records_map(
            anilist_id_status_map={anime.id: anime.status for anime in anime_records},
            force_fetch=params.force_freshness
        )
        user_list = await self._anilist_list_component.get_user_anime_list(force_fetch=params.force_freshness) \
            if config.user_settings.anilist_user_token else None
        tracked_anime = await self._tracked_anime_component.get_tracked_anime_by_anilist_ids(
            anilist_ids=list([anime.id for anime in anime_records]), load_relations=False
        )
        anilist_id_tracked_anime_id = {tracked.anilist_id: tracked.id for tracked in tracked_anime
                                       if tracked.status == TrackedAnimeStatus.ACTIVE}
        return AnimeListResponse(
            anime=[
                self._to_anime_item(
                    anime=anime,
                    airing_schedule=airing_schedules.get(anime.id) or [],
                    user_entry=user_list.get_entry_by_anime_id(anime_id=anime.id) if user_list else None,
                    tracked_anime_id=anilist_id_tracked_anime_id.get(anime.id),
                    tvdb_series_id=await anime_relations.get_anilist_id_tvdb_series_id(anime.id)
                )
                for anime in anime_records
            ]
        )

    @api_component
    async def get_anime(self, anilist_id: int, force_freshness: bool = False) -> AnimeItemWithUserEntry:
        anime = await self._anilist_component.get_anime(
            anilist_anime_id=anilist_id,
            force_refresh=force_freshness,
        )
        if anime is None:
            raise AnilistNotFoundException(f"No anime found for id: {anilist_id}")
        airing_schedules = await self._anilist_airing_schedule_component.get_future_anime_schedule_records_map(
            anilist_id_status_map={anime.id: anime.status},
            force_fetch=force_freshness
        )
        user_entry = await self._anilist_list_component.get_user_anime_list_entry(anilist_id=anilist_id,
                                                                                  force_fetch=force_freshness) \
            if config.user_settings.anilist_user_token else None
        tracked_anime = await self._tracked_anime_component.get_tracked_anime(
            anilist_id=anilist_id, load_relations=False
        )
        return self._to_anime_item(anime=anime, airing_schedule=airing_schedules.get(anilist_id) or [],
                                   user_entry=user_entry,
                                   tracked_anime_id=tracked_anime.id
                                   if tracked_anime and tracked_anime.status == TrackedAnimeStatus.ACTIVE
                                   else None,
                                   tvdb_series_id=await anime_relations.get_anilist_id_tvdb_series_id(anilist_id))

    @api_component
    async def get_anilist_metadata(self) -> AnilistMetadataResponse:
        genres, tags = await self._anilist_service.get_genre_and_tag_collections()
        return AnilistMetadataResponse(
            genres=genres,
            tags=[
                AnilistMetadataResponse.AnilistMetadataTag(name=tag["name"], category=tag["category"])
                for tag in tags
            ],
        )

    @staticmethod
    def _to_anime_item(anime: AnilistAnime,
                       airing_schedule: list[AnilistAiringScheduleItem],
                       user_entry: AnilistUserListEntry | None,
                       tracked_anime_id: int | None,
                       tvdb_series_id: int | None) -> AnimeItemWithUserEntry:
        next_airing_episode = None
        if airing_schedule:
            next_airing_episode = sorted(airing_schedule, key=lambda x: x.airing_at)[0]
            next_airing_episode = AnilistItemAiringScheduleItem(
                airing_at=next_airing_episode.airing_at,
                episode=next_airing_episode.episode,
                anilist_id=next_airing_episode.anilist_id,
            )
        return AnimeItemWithUserEntry(
            id=anime.id,
            idMal=anime.idMal,
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
            description=anime.description,
            source=anime.source,
            popularity=anime.popularity,
            duration=anime.duration,
            country_of_origin=anime.country_of_origin,
            hashtag=anime.hashtag,
            synonyms=anime.synonyms,
            start_date=AnimeItem.AnilistDate(year=anime.start_date.year,
                                             month=anime.start_date.month,
                                             day=anime.start_date.day),
            end_date=AnimeItem.AnilistDate(year=anime.end_date.year,
                                           month=anime.end_date.month,
                                           day=anime.end_date.day),
            genres=anime.genres,
            tags=[AnimeItem.AnilistTag(name=tag.name,
                                       rank=tag.rank,
                                       is_media_spoiler=tag.is_media_spoiler,
                                       is_general_spoiler=tag.is_general_spoiler)
                  for tag in anime.tags],
            is_adult=anime.is_adult,
            studios=[AnimeItem.AnilistStudio(name=studio.name, site_url=studio.site_url, is_primary=studio.is_primary)
                     for studio in anime.studios],
            trailer_url=anime.trailer_url,
            external_links=[AnimeItem.AnilistExternalLink(site=link.site, url=link.url)
                            for link in anime.external_links],
            user_entry=AnimeItemWithUserEntry.UserEntry(
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
            tracked_anime_id=tracked_anime_id
        )

    @api_component
    async def get_anime_extras(self, anilist_id: int, force_freshness: bool) -> AnimeExtras:
        extras = await self._anilist_component.get_anime_extras(anilist_id=anilist_id,
                                                                force_fetch=force_freshness)
        user_entry = await self._anilist_list_component.get_user_anime_list_entry(anilist_id=anilist_id,
                                                                                  force_fetch=force_freshness) \
            if config.user_settings.anilist_user_token else None

        def dig(source, path):
            value = source
            for key in path:
                if value is None:
                    return None
                try:
                    value = value[key]
                except (KeyError, IndexError, TypeError):
                    return None
            return value

        return AnimeExtras(
            characters=[
                AnimeExtras.Character(
                    site_url=dig(edge, ("node", "siteUrl")),
                    image_url=dig(edge, ("node", "image", "large")),
                    name=dig(edge, ("node", "name", "full")),
                    role=dig(edge, ("role",)),
                    voice_actor=AnimeExtras.Character.CharacterStaff(
                        site_url=dig(edge, ("voiceActorRoles", 0, "voiceActor", "siteUrl")),
                        image_url=dig(edge, ("voiceActorRoles", 0, "voiceActor", "image", "large")),
                        name=dig(edge, ("voiceActorRoles", 0, "voiceActor", "name", "full")),
                    ) if dig(edge, ("voiceActorRoles", 0)) else None,
                )
                for edge in dig(extras, ("characters", "edges")) or []
            ],
            relations=[
                AnimeExtras.Relation(
                    id=dig(edge, ("node", "id")),
                    image_url=dig(edge, ("node", "coverImage", "large")),
                    english_title=dig(edge, ("node", "title", "english")),
                    romaji_title=dig(edge, ("node", "title", "romaji")),
                    native_title=dig(edge, ("node", "title", "native")),
                    format=AnilistFormat(dig(edge, ("node", "format")))
                    if dig(edge, ("node", "format"))
                    else None,
                    relation_type=dig(edge, ("relationType",)),
                    list_status=user_entry.status
                    if user_entry and dig(edge, ("node", "format")) in AnilistAnimeFormat.as_list()
                    else None
                )
                for edge in dig(extras, ("relations", "edges")) or []
            ],
            staff=[
                AnimeExtras.Staff(
                    site_url=dig(edge, ("node", "siteUrl")),
                    image_url=dig(edge, ("node", "image", "large")),
                    name=dig(edge, ("node", "name", "full")),
                    role=dig(edge, ("role",)),
                )
                for edge in dig(extras, ("staff", "edges")) or []
            ],
        )

    async def get_anime_titles(self, anilist_id: int, force_freshness: bool) -> AnimeTitlesResponse:
        anime = await self._anilist_component.get_anime(anilist_anime_id=anilist_id, force_refresh=force_freshness)
        if not anime:
            raise AnilistNotFoundException(f"No anime found for id: {anilist_id}")
        titles = []
        if anime.romaji_title:
            titles.append(AnimeTitlesResponse.Title(source=MetadataSource.ANILIST,
                                                    title=anime.romaji_title,
                                                    language="Romaji"))
        if anime.english_title:
            titles.append(AnimeTitlesResponse.Title(source=MetadataSource.ANILIST,
                                                    title=anime.english_title,
                                                    language="English"))
        if anime.native_title:
            titles.append(AnimeTitlesResponse.Title(source=MetadataSource.ANILIST,
                                                    title=anime.native_title,
                                                    language="Native"))

        try:
            tvdb_series_id = await anime_relations.get_anilist_id_tvdb_series_id(anilist_id)
            if tvdb_series_id:
                tvdb_series = await TVDBComponent().get_series(
                    series_id=tvdb_series_id, minimum_freshness=timedelta(seconds=1) if force_freshness else None
                )
                for alias in tvdb_series.aliases:
                    titles.append(AnimeTitlesResponse.Title(source=MetadataSource.TVDB,
                                                            title=alias.title,
                                                            language=alias.language))
        except Exception as e:
            self.logger.info(f"Failed to fetch tvdb series for anime {anilist_id}: {e}")

        return AnimeTitlesResponse(titles=titles)
