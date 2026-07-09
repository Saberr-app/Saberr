import asyncio

from app_state import anime_relations
from common.db import get_session
from common.decorators import api_component
from common.exceptions import ExternalServiceException, ObjectNotFoundException, ValidationException
from components import BaseComponent
from components.audit_log_component import AuditLogComponent
from components.service_components.anilist_component import AnilistComponent
from components.service_components.tvdb_component import TVDBComponent
from constants import AuditLogCode
from dto.anilist import AnilistAnime
from dto.orm_models import MappingOverride
from dto.tvdb import TVDBSeries
from api.schemas.mapping_schemas import MappingOverrideListResponse, MappingOverrideItem, MappingOverrideRequest, \
    MappingStatsResponse
from repositories.mapping_override_repo import MappingOverrideRepo


class MappingAPIComponent(BaseComponent):

    def __init__(self):
        super().__init__()
        self._anilist_component = AnilistComponent()
        self._tvdb_component = TVDBComponent()

    @api_component
    async def get_mapping_overrides(self) -> MappingOverrideListResponse:
        overrides = await MappingOverrideRepo(get_session()).get_all_mapping_overrides()
        anime_map = {anime.id: anime for anime in await self._anilist_component.get_anime_records(
            anilist_anime_ids={override.anilist_id for override in overrides}
        )}
        series_ids = {override.tvdb_series_id for override in overrides}
        series_records = await asyncio.gather(*[self._tvdb_component.get_series(series_id=series_id)
                                                for series_id in series_ids])
        series_map = {series_id: series for series_id, series in zip(series_ids, series_records)}
        return MappingOverrideListResponse(mapping_overrides=[
            self._to_item(override=override,
                          anime=anime_map.get(override.anilist_id),
                          series=series_map.get(override.tvdb_series_id))
            for override in overrides
        ])

    @api_component
    async def create_mapping_override(self, body: MappingOverrideRequest) -> MappingOverrideItem:
        self._validate_ranges(body)
        anime = await self._get_anilist_anime(body.anilist_id)
        series = await self._get_tvdb_series(body.tvdb_series_id)
        override = await MappingOverrideRepo(get_session()).create_mapping_override(
            anilist_id=body.anilist_id,
            anilist_episode_number_from=body.anilist_episode_number_from,
            anilist_episode_number_to=body.anilist_episode_number_to,
            tvdb_series_id=body.tvdb_series_id,
            tvdb_season_number=body.tvdb_season_number,
            tvdb_episode_number_from=body.tvdb_episode_number_from,
            tvdb_episode_number_to=body.tvdb_episode_number_to,
            granularity=body.granularity,
            mode=body.mode,
        )
        await AuditLogComponent().log_mapping_override_added_or_removed(
            code=AuditLogCode.MAPPING_OVERRIDE_ADDED, anilist_id=body.anilist_id,
            anilist_from_episode=body.anilist_episode_number_from, anilist_to_episode=body.anilist_episode_number_to,
            tvdb_series_id=body.tvdb_series_id, tvdb_season_number=body.tvdb_season_number,
            tvdb_from_episode=body.tvdb_episode_number_from, tvdb_to_episode=body.tvdb_episode_number_to,
            granularity=body.granularity, mode=body.mode,
            anilist_title=anime.romaji_title, tvdb_series_title=series.english_title
        )
        return self._to_item(override=override, anime=anime, series=series)

    @api_component
    async def update_mapping_override(self, mapping_override_id: int,
                                      body: MappingOverrideRequest) -> MappingOverrideItem:
        mapping_override_repo = MappingOverrideRepo(get_session())
        override = await mapping_override_repo.get_mapping_override(mapping_override_id)
        if override is None:
            raise ObjectNotFoundException(f"Mapping override not found: {mapping_override_id}")
        self._validate_ranges(body)
        anime = await self._get_anilist_anime(body.anilist_id)
        series = await self._get_tvdb_series(body.tvdb_series_id)
        update_data, updated_data = self._get_update_diff(override, body)
        await mapping_override_repo.update_mapping_override(
            override_id=mapping_override_id,
            data=update_data
        )
        override = await mapping_override_repo.get_mapping_override(mapping_override_id)
        await AuditLogComponent().log_mapping_override_updated(
            updated_data=updated_data,
            anilist_id=body.anilist_id if "anilist_id" not in update_data else None,
            tvdb_series_id=body.tvdb_series_id if "tvdb_series_id" not in update_data else None,
            anilist_title=anime.romaji_title if "anilist_id" not in update_data else None,
            tvdb_series_title=series.english_title if "tvdb_series_id" not in update_data else None
        )
        return self._to_item(override=override, anime=anime, series=series)

    @api_component
    async def delete_mapping_override(self, mapping_override_id: int) -> None:
        mapping_override_repo = MappingOverrideRepo(get_session())
        override = await mapping_override_repo.get_mapping_override(mapping_override_id)
        if override is None:
            raise ObjectNotFoundException(f"Mapping override not found: {mapping_override_id}")
        await mapping_override_repo.delete_mapping_override(mapping_override_id)
        try:
            anime = await self._get_anilist_anime(override.anilist_id)
            series = await self._get_tvdb_series(override.tvdb_series_id)
            anilist_title = anime.romaji_title
            tvdb_series_title = series.english_title
        except (ExternalServiceException, ValidationException):
            anilist_title = None
            tvdb_series_title = None
        await AuditLogComponent().log_mapping_override_added_or_removed(
            code=AuditLogCode.MAPPING_OVERRIDE_DELETED, anilist_id=override.anilist_id,
            anilist_from_episode=override.anilist_episode_number_from,
            anilist_to_episode=override.anilist_episode_number_to,
            tvdb_series_id=override.tvdb_series_id, tvdb_season_number=override.tvdb_season_number,
            tvdb_from_episode=override.tvdb_episode_number_from, tvdb_to_episode=override.tvdb_episode_number_to,
            granularity=override.granularity, mode=override.mode,
            anilist_title=anilist_title, tvdb_series_title=tvdb_series_title
        )

    @api_component
    async def get_mapping_stats(self) -> MappingStatsResponse:
        return MappingStatsResponse(
            anime_relations_count=anime_relations.anime_relations_offset_map_count,
            anilist_tvdb_mappings_count=anime_relations.anilist_tvdb_mappings_count,
            anime_relations_last_updated_at=await anime_relations.anime_relations_offset_map_last_updated(),
            anilist_tvdb_mappings_last_updated_at=await anime_relations.anilist_tvdb_mappings_last_updated(),
        )

    @api_component
    async def refresh_mappings(self) -> None:
        await anime_relations.refresh_relations(raise_on_failure=True)

    async def _get_anilist_anime(self, anilist_id: int) -> AnilistAnime:
        anime = await self._anilist_component.get_anime(anilist_anime_id=anilist_id)
        if anime is None:
            raise ValidationException(f"No AniList anime found for id: {anilist_id}")
        return anime

    async def _get_tvdb_series(self, tvdb_series_id: int) -> TVDBSeries:
        try:
            return await self._tvdb_component.get_series(series_id=tvdb_series_id)
        except ExternalServiceException as e:
            if e.status_code == 404:
                raise ValidationException(f"No TVDB series found for id: {tvdb_series_id}") from e
            raise

    @staticmethod
    def _validate_ranges(body: MappingOverrideRequest) -> None:
        if not (body.granularity >= 1 or body.granularity <= -2):
            raise ValidationException("Granularity must be 1 or higher, or -2 or lower.")
        if (body.anilist_episode_number_to is None) != (body.tvdb_episode_number_to is None):
            raise ValidationException("AniList and TVDB episode 'to' must both be set or both be null.")
        if body.anilist_episode_number_to is not None \
                and body.anilist_episode_number_from > body.anilist_episode_number_to:
            raise ValidationException("AniList episode 'from' must be less than or equal to 'to'.")
        if body.tvdb_episode_number_to is not None \
                and body.tvdb_episode_number_from > body.tvdb_episode_number_to:
            raise ValidationException("TVDB episode 'from' must be less than or equal to 'to'.")
        if body.anilist_episode_number_to is not None:
            ani_count = body.anilist_episode_number_to - body.anilist_episode_number_from + 1
            tvdb_count = body.tvdb_episode_number_to - body.tvdb_episode_number_from + 1
            if body.granularity == 1 and ani_count != tvdb_count:
                raise ValidationException("With granularity 1 the AniList and TVDB episode counts must be equal.")
            if body.granularity >= 2 and ani_count != body.granularity * tvdb_count:
                raise ValidationException("The AniList episode count must equal granularity times the TVDB "
                                          "episode count.")
            if body.granularity <= -2 and tvdb_count != -body.granularity * ani_count:
                raise ValidationException("The TVDB episode count must equal |granularity| times the AniList "
                                          "episode count.")

    @staticmethod
    def _to_item(override: MappingOverride,
                 anime: AnilistAnime,
                 series: TVDBSeries) -> MappingOverrideItem:
        return MappingOverrideItem(
            id=override.id,
            anilist_id=override.anilist_id,
            anilist_episode_number_from=override.anilist_episode_number_from,
            anilist_episode_number_to=override.anilist_episode_number_to,
            tvdb_series_id=override.tvdb_series_id,
            tvdb_season_number=override.tvdb_season_number,
            tvdb_episode_number_from=override.tvdb_episode_number_from,
            tvdb_episode_number_to=override.tvdb_episode_number_to,
            granularity=override.granularity,
            mode=override.mode,
            anilist_english_title=anime.english_title,
            anilist_native_title=anime.native_title,
            anilist_romaji_title=anime.romaji_title,
            anilist_small_cover_image=anime.small_cover_image,
            tvdb_title=series.english_title or series.title,
            tvdb_image_url=series.image_url,
        )

    @staticmethod
    def _get_update_diff(override: MappingOverride, update_body: MappingOverrideRequest) -> tuple[dict, dict]:
        update_data, updated_data = {}, {}
        if update_body.anilist_id != override.anilist_id:
            update_data["anilist_id"] = update_body.anilist_id
            updated_data["AniList ID"] = {"old": override.anilist_id,
                                          "new": update_body.anilist_id}
        if update_body.anilist_episode_number_from != override.anilist_episode_number_from:
            update_data["anilist_episode_number_from"] = update_body.anilist_episode_number_from
            updated_data["AniList episode 'from'"] = {"old": override.anilist_episode_number_from,
                                                      "new": update_body.anilist_episode_number_from}
        if update_body.anilist_episode_number_to != override.anilist_episode_number_to:
            update_data["anilist_episode_number_to"] = update_body.anilist_episode_number_to
            updated_data["AniList episode 'to'"] = {"old": override.anilist_episode_number_to,
                                                    "new": update_body.anilist_episode_number_to}
        if update_body.tvdb_series_id != override.tvdb_series_id:
            update_data["tvdb_series_id"] = update_body.tvdb_series_id
            updated_data["TVDB series ID"] = {"old": override.tvdb_series_id,
                                              "new": update_body.tvdb_series_id}
        if update_body.tvdb_season_number != override.tvdb_season_number:
            update_data["tvdb_season_number"] = update_body.tvdb_season_number
            updated_data["TVDB season number"] = {"old": override.tvdb_season_number,
                                                  "new": update_body.tvdb_season_number}
        if update_body.tvdb_episode_number_from != override.tvdb_episode_number_from:
            update_data["tvdb_episode_number_from"] = update_body.tvdb_episode_number_from
            updated_data["TVDB episode 'from'"] = {"old": override.tvdb_episode_number_from,
                                                   "new": update_body.tvdb_episode_number_from}
        if update_body.tvdb_episode_number_to != override.tvdb_episode_number_to:
            update_data["tvdb_episode_number_to"] = update_body.tvdb_episode_number_to
            updated_data["TVDB episode 'to'"] = {"old": override.tvdb_episode_number_to,
                                                 "new": update_body.tvdb_episode_number_to}
        if update_body.granularity != override.granularity:
            update_data["granularity"] = update_body.granularity
            updated_data["Granularity"] = {"old": override.granularity, "new": update_body.granularity}
        if update_body.mode != override.mode:
            update_data["mode"] = update_body.mode
            updated_data["Mode"] = {"old": override.mode.value.replace('_', ' ').capitalize(),
                                    "new": update_body.mode.value.replace('_', ' ').capitalize()}

        return update_data, updated_data
