import asyncio
import io
import json
import logging
import re
from datetime import datetime, UTC, timedelta

from common.context_helpers import create_task
from common.decorators import require_db_session
from common.exceptions import ExternalServiceException, AnilistRelationsEpisodeCountMismatch
from common.db import get_session
from config import config
from constants import CachedAssetType, MappingOverrideMode
from dto.orm_models import MappingOverride
from dto.tvdb import AnilistEpisodeTVDBMapping, TVDBEpisodeAnilistMapping
from repositories.mapping_override_repo import MappingOverrideRepo


class AnimeRelations:
    MAPPINGS_FILENAME = 'mappings.min.json'
    HOT_OVERRIDES_FILENAME = 'overrides.min.json'
    OFFSET_MAP_FILENAME = 'anime-relations.txt'
    OFFSET_EPISODE_COUNT_MAP_FILENAME = 'anime-relations-anilist-episode-count.txt'

    def __init__(self):
        from components.asset_component import AssetComponent
        self.asset_component = AssetComponent()

        self._ANILIST_TVDB_MAPPINGS = {}
        self._TVDB_ANILIST_MAPPINGS = {}
        self._ANIME_RELATIONS_OFFSET_MAP = {}
        self._ANIME_RELATIONS_OFFSET_EPISODE_COUNT_MAP = {}

        self.last_synced = None
        self._lock = asyncio.Lock()
        self.logger = logging.getLogger(self.__class__.__name__)

    @require_db_session
    async def load_relations(self):  # not necessarily fresh, called on app start and on mappings settings changes
        self.logger.debug("Loading anime relations data...")
        refresh_needed = False
        try:
            external_mappings_bytes = await self.asset_component.get_asset_data_by_filename(
                asset_filename=self.MAPPINGS_FILENAME,
                asset_type=CachedAssetType.RELATIONS,
                expired_ok=True,
                lifespan=timedelta(days=1)
            )
        except Exception as e:
            self.logger.error(f"Failed to load external mappings data: {e}")
            external_mappings_bytes = b'{}'
            refresh_needed = True
        anilist_tvdb_mappings, tvdb_anilist_mappings = self._build_external_mappings(external_mappings_bytes)
        self.logger.info(f"Loaded {len(anilist_tvdb_mappings)} anilist-tvdb mappings, "
                         f"{len(tvdb_anilist_mappings)} tvdb-anilist mappings")
        if config.user_settings.hot_mapping_overrides_enabled:
            try:
                mapping_overrides_bytes = await self.asset_component.get_asset_data_by_filename(
                    asset_filename=self.HOT_OVERRIDES_FILENAME,
                    asset_type=CachedAssetType.RELATIONS,
                    expired_ok=True,
                    lifespan=timedelta(days=1)
                )
            except Exception as e:
                self.logger.error(f"Failed to load hot overrides: {e}")
                mapping_overrides_bytes = b'{"mappings": {}}'
                refresh_needed = True
            self._override_external_mappings(anilist_tvdb_mappings, tvdb_anilist_mappings, mapping_overrides_bytes)
            self.logger.info(f"Applied hot mapping overrides")
        try:
            offset_map_bytes = await self.asset_component.get_asset_data_by_filename(
                asset_filename=self.OFFSET_MAP_FILENAME,
                asset_type=CachedAssetType.RELATIONS,
                expired_ok=True,
                lifespan=timedelta(days=1)
            )
        except Exception as e:
            self.logger.error(f"Failed to load anime relations offset map: {e}")
            offset_map_bytes = b''
            refresh_needed = True
        offset_map = self._build_anime_relations_offset_map(offset_map_bytes)
        self.logger.info(f"Loaded {len(offset_map)} anime relations offset map entries")

        try:
            anilist_episode_count_bytes = await self.asset_component.get_asset_data_by_filename(
                asset_filename=self.OFFSET_EPISODE_COUNT_MAP_FILENAME,
                asset_type=CachedAssetType.RELATIONS,
                expired_ok=True,
                lifespan=timedelta(days=1)
            )
        except Exception as e:
            self.logger.error(f"Failed to load anilist-episode-count mappings: {e}")
            anilist_episode_count_bytes = b''
            refresh_needed = True
        offset_anilist_episode_count = self._build_anilist_episode_count_map(anilist_episode_count_bytes)
        self.logger.info(f"Loaded {len(offset_anilist_episode_count)} anilist-episode-count mappings")

        async with self._lock:
            self._ANILIST_TVDB_MAPPINGS.clear()
            self._ANILIST_TVDB_MAPPINGS.update(anilist_tvdb_mappings)
            self._TVDB_ANILIST_MAPPINGS.clear()
            self._TVDB_ANILIST_MAPPINGS.update(tvdb_anilist_mappings)
            self._ANIME_RELATIONS_OFFSET_MAP.clear()
            self._ANIME_RELATIONS_OFFSET_MAP.update(offset_map)
            self._ANIME_RELATIONS_OFFSET_EPISODE_COUNT_MAP.clear()
            self._ANIME_RELATIONS_OFFSET_EPISODE_COUNT_MAP.update(offset_anilist_episode_count)

        if refresh_needed:
            create_task(self.refresh_relations())

    async def refresh_relations(self, raise_on_failure: bool = False):  # strictly fresh
        self.logger.info("Refreshing anime relations data...")
        try:
            anilist_tvdb_mappings, tvdb_anilist_mappings = self._build_external_mappings(
                await self.asset_component.get_asset_data_by_filename(
                    asset_filename=self.MAPPINGS_FILENAME,
                    asset_type=CachedAssetType.RELATIONS,
                    lifespan=timedelta(days=1),
                    force_fetch=True
                )
            )
            self.logger.debug(f"Refreshed {len(anilist_tvdb_mappings)} anilist-tvdb mappings, "
                              f"{len(tvdb_anilist_mappings)} tvdb-anilist mappings")
            if config.user_settings.hot_mapping_overrides_enabled:
                self._override_external_mappings(
                    anilist_tvdb_mappings, tvdb_anilist_mappings,
                    await self.asset_component.get_asset_data_by_filename(
                        asset_filename=self.HOT_OVERRIDES_FILENAME,
                        asset_type=CachedAssetType.RELATIONS,
                        lifespan=timedelta(days=1),
                        force_fetch=True
                    )
                )
                self.logger.debug(f"Applied hot mapping overrides")
            offset_map = self._build_anime_relations_offset_map(
                await self.asset_component.get_asset_data_by_filename(
                    asset_filename=self.OFFSET_MAP_FILENAME,
                    asset_type=CachedAssetType.RELATIONS,
                    lifespan=timedelta(days=1),
                    force_fetch=True
                )
            )
            self.logger.debug(f"Refreshed {len(offset_map)} anime relations offset map entries")
            offset_anilist_episode_count = self._build_anilist_episode_count_map(
                await self.asset_component.get_asset_data_by_filename(
                    asset_filename=self.OFFSET_EPISODE_COUNT_MAP_FILENAME,
                    asset_type=CachedAssetType.RELATIONS,
                    lifespan=timedelta(days=1),
                    force_fetch=True
                )
            )
            self.logger.debug(f"Refreshed {len(offset_anilist_episode_count)} anilist-episode-count mappings")
            async with self._lock:
                self._ANILIST_TVDB_MAPPINGS.clear()
                self._ANILIST_TVDB_MAPPINGS.update(anilist_tvdb_mappings)
                self._TVDB_ANILIST_MAPPINGS.clear()
                self._TVDB_ANILIST_MAPPINGS.update(tvdb_anilist_mappings)
                self._ANIME_RELATIONS_OFFSET_MAP.clear()
                self._ANIME_RELATIONS_OFFSET_MAP.update(offset_map)
                self._ANIME_RELATIONS_OFFSET_EPISODE_COUNT_MAP.clear()
                self._ANIME_RELATIONS_OFFSET_EPISODE_COUNT_MAP.update(offset_anilist_episode_count)
            self.last_synced = datetime.now(UTC)
        except ExternalServiceException as e:
            self.logger.warning(f"Failed to refresh anime relations data: {e}")
            if raise_on_failure:
                raise e

    async def get_anilist_episode_tvdb_mappings(self,
                                                anilist_id: int,
                                                episode_number: int) -> list[AnilistEpisodeTVDBMapping]:
        overrides = await MappingOverrideRepo(get_session()).get_mapping_overrides_for_anime(anilist_id=anilist_id)
        override_mappings, _ = self._overrides_to_mappings(overrides)

        override_results, is_strict_override = await self._get_anilist_episode_tvdb_mappings(anilist_id,
                                                                                             episode_number,
                                                                                             mappings=override_mappings)
        if is_strict_override:
            return override_results

        anibridge_results, _ = await self._get_anilist_episode_tvdb_mappings(anilist_id, episode_number)
        return anibridge_results or override_results

    async def _get_anilist_episode_tvdb_mappings(self,
                                                 anilist_id: int,
                                                 episode_number: int,
                                                 mappings: dict | None = None
                                                 ) -> tuple[list[AnilistEpisodeTVDBMapping], bool]:
        async with self._lock:
            mappings = mappings if mappings is not None else self._ANILIST_TVDB_MAPPINGS
            if not mappings or anilist_id not in mappings:
                return [], False

            series_key, targets, is_strict_override = self._pick_resolved_targets(
                (series_key, self._resolve_mapping_targets(episode_number, source_map))
                for series_key, source_map in sorted(mappings[anilist_id].items(), reverse=True)
            )
            return [AnilistEpisodeTVDBMapping(
                series_id=series_key[0],
                season_number=series_key[1],
                episode_number=target_episode,
                part=part,
                part_ceiling=part_ceiling
            ) for target_episode, part, part_ceiling, _ in targets], is_strict_override

    async def get_tvdb_episode_anilist_mappings(self,
                                                series_id: int,
                                                season_number: int,
                                                episode_number: int) -> list[TVDBEpisodeAnilistMapping]:
        overrides = await MappingOverrideRepo(get_session()).get_mapping_overrides_for_anime(tvdb_id=series_id)
        _, override_mappings = self._overrides_to_mappings(overrides)

        override_results, is_strict_override = await self._get_tvdb_episode_anilist_mappings(series_id,
                                                                                             season_number,
                                                                                             episode_number,
                                                                                             mappings=override_mappings)
        if is_strict_override:
            return override_results

        anibridge_results, _ = await self._get_tvdb_episode_anilist_mappings(series_id, season_number, episode_number)
        return anibridge_results or override_results

    async def _get_tvdb_episode_anilist_mappings(self,
                                                 series_id: int,
                                                 season_number: int,
                                                 episode_number: int,
                                                 mappings: dict | None = None
                                                 ) -> tuple[list[TVDBEpisodeAnilistMapping], bool]:
        async with self._lock:
            mappings = mappings if mappings is not None else self._TVDB_ANILIST_MAPPINGS
            series_key = (series_id, season_number)
            if not mappings or series_key not in mappings:
                return [], False

            anilist_id, targets, is_strict_override = self._pick_resolved_targets(
                (anilist_id, self._resolve_mapping_targets(episode_number, source_map))
                for anilist_id, source_map in sorted(mappings[series_key].items(), reverse=True)
            )
            return [TVDBEpisodeAnilistMapping(
                anilist_id=anilist_id,
                episode_number=target_episode,
                part=part,
                part_ceiling=part_ceiling
            ) for target_episode, part, part_ceiling, _ in targets], is_strict_override

    async def get_anilist_id_tvdb_series_id(self, anilist_id: int) -> int | None:
        overrides = await MappingOverrideRepo(get_session()).get_mapping_overrides_for_anime(anilist_id=anilist_id)
        override_mappings, _ = self._overrides_to_mappings(overrides)

        override_series_id, is_strict_override = await self._get_anilist_id_tvdb_series_id(anilist_id,
                                                                                           mappings=override_mappings)
        if is_strict_override:
            return override_series_id

        anibridge_series_id, _ = await self._get_anilist_id_tvdb_series_id(anilist_id)
        return anibridge_series_id if anibridge_series_id is not None else override_series_id

    async def _get_anilist_id_tvdb_series_id(self,
                                             anilist_id: int,
                                             mappings: dict | None = None) -> tuple[int | None, bool]:
        async with self._lock:
            mappings = mappings if mappings is not None else self._ANILIST_TVDB_MAPPINGS
            if not mappings or not mappings.get(anilist_id):
                return None, False

            def season_priority(series_key: tuple[int, int]) -> tuple[float, int]:
                series_id, season_number = series_key
                if season_number == 0:
                    return float('inf'), series_id
                return season_number, series_id

            strict_series_keys = [series_key for series_key, source_map in mappings[anilist_id].items()
                                  if any(mode == MappingOverrideMode.ALWAYS
                                         for targets in source_map.values()
                                         for _, _, _, mode in targets)]
            best_series_key = min(strict_series_keys or mappings[anilist_id], key=season_priority)
            return best_series_key[0], bool(strict_series_keys)

    @staticmethod
    def _pick_resolved_targets(resolved_by_key) -> tuple:
        # resolved_by_key yields (key, targets) in lookup order, the first key with strict (ALWAYS) targets wins
        first_resolved = None
        for key, targets in resolved_by_key:
            strict_targets = [target for target in targets if target[3]]
            if strict_targets:
                return key, strict_targets, True
            if targets and first_resolved is None:
                first_resolved = (key, targets, False)
        return first_resolved or (None, [], False)

    @staticmethod
    def _resolve_mapping_targets(
            episode_number: int,
            source_map: dict[tuple[int, int | None], list[tuple[int, int | None, int, MappingOverrideMode | None]]]
    ) -> list[tuple[int, int | None, int | None, bool]]:
        # maps a source episode number through a single source_map, returning
        # (target_episode, part, part_ceiling, is_strict_override) tuples.
        # part/part_ceiling are only set when several source episodes collapse into one target (step > 1),
        # e.g. part 3 of 4 -> part=3, part_ceiling=4.
        # is_strict_override is True when the target comes from an ALWAYS-mode user override or a hot override.
        results: list[tuple[int, int | None, int | None, bool]] = []
        for (source_start, source_end), target_list in source_map.items():
            if episode_number < source_start:
                continue
            if source_end is not None and episode_number > source_end:
                continue

            offset = episode_number - source_start
            for target_start, target_end, step, mode in target_list:
                if step == 0:
                    continue
                is_strict_override = mode == MappingOverrideMode.ALWAYS
                if step > 0:
                    target_episode = target_start + (offset // step)
                    if target_end is not None and target_episode > target_end:
                        continue
                    part = (offset % step) + 1 if step > 1 else None
                    part_ceiling = step if step > 1 else None
                    results.append((target_episode, part, part_ceiling, is_strict_override))
                else:
                    group_size = abs(step)
                    target_episode_start = target_start + (offset * group_size)
                    if target_end is not None and target_episode_start > target_end:
                        continue
                    target_episode_end = target_episode_start + group_size - 1
                    if target_end is not None:
                        target_episode_end = min(target_episode_end, target_end)
                    for target_episode in range(target_episode_start, target_episode_end + 1):
                        results.append((target_episode, None, None, is_strict_override))

        return results

    async def resolve_anime(self, original_anilist_id: int, original_episode_number: int) -> tuple[int, int]:
        async with self._lock:
            offset_map = self._ANIME_RELATIONS_OFFSET_MAP
            episode_count_map = self._ANIME_RELATIONS_OFFSET_EPISODE_COUNT_MAP
            visited = set()
            current_anilist_id = original_anilist_id
            current_episode_number = original_episode_number

            while True:
                state = (current_anilist_id, current_episode_number)
                if state in visited:
                    return current_anilist_id, current_episode_number
                visited.add(state)

                # https://github.com/erengy/anime-relations/issues/27#issuecomment-408691860
                if episode_count := episode_count_map.get(current_anilist_id):
                    if current_episode_number in range(1, episode_count + 1):
                        return current_anilist_id, current_episode_number

                if current_anilist_id not in offset_map:
                    return current_anilist_id, current_episode_number

                relations = offset_map[current_anilist_id].get('relations', [])
                if not relations:
                    return current_anilist_id, current_episode_number

                matched_relation = None
                for relation in relations:
                    this_start, this_end = relation['this_episode_range']
                    if this_start <= current_episode_number <= this_end:
                        matched_relation = relation
                        break

                if not matched_relation:
                    return current_anilist_id, current_episode_number

                other_start, other_end = matched_relation['other_episode_range']
                this_start, this_end = matched_relation['this_episode_range']
                this_length = this_end - this_start
                other_length = other_end - other_start
                if this_length != other_length:
                    detail = ("Episode range mismatch for "
                              f"{current_anilist_id}:{this_start}-{this_end} -> "
                              f"{matched_relation['other_anilist_id']}:{other_start}-{other_end}; "
                              f"episode {current_episode_number} cannot be mapped.")
                    raise AnilistRelationsEpisodeCountMismatch(detail)

                mapped_episode_number = other_start + (current_episode_number - this_start)
                mapped_anilist_id = matched_relation['other_anilist_id']

                if mapped_anilist_id == current_anilist_id and mapped_episode_number == current_episode_number:
                    return current_anilist_id, current_episode_number

                current_anilist_id = mapped_anilist_id
                current_episode_number = mapped_episode_number

    @staticmethod
    def _build_external_mappings(
            source_data: bytes
    ) -> tuple[
        dict[int, dict[tuple[int, int], dict[tuple[int, int | None], list[tuple[int, int | None, int, None]]]]],
        dict[tuple[int, int], dict[int, dict[tuple[int, int | None], list[tuple[int, int | None, int, None]]]]],
    ]:
        # anibridge mappings parser
        anilist_tvdb = {
            # anilist_id
            #  (tvdb_series_id, season_number)
            #       (range_start, range_end or none) -> [(range_start, range_end or none, granularity step)]
            # step could be positive or negative, e.g. for step=x, a positive step means:
            #  x eps on the left side map to 1 on the right size, and vice versa for a negative step
            #  e.g. anilist:151799 tvdb_show:188551:s2, '3-5': '4-12|-3'
            #  means anilist episode 3 maps to tvdb episodes 4, 5, and 6, 4 to 7, 8, and 9, and 5 to 10, 11, and 12
            #  e.g. anilist:151700 tvdb_show:188550:s1, '1-2': '1|2'
            #  means anilist episodes 1 and 2 maps to tvdb episode 1
        }
        tvdb_anilist = {
            # the reverse direction, built from the top-level tvdb_show:<series>:s<season> entries
            # (tvdb_series_id, season_number)
            #  anilist_id
            #       (range_start, range_end or none) -> [(range_start, range_end or none, granularity step)]
            # here the source ranges are tvdb episodes and the targets are anilist episodes
            #  e.g. tvdb_show:188551:s2 anilist:151799, '4-12': '3-5|-3'
            #  means tvdb episodes 4, 5, and 6 map to anilist episode 3, 7-9 to 4, and 10-12 to 5
        }

        def parse_range(range_str: str) -> tuple[int, int | None]:
            range_parts = range_str.split("-")
            if len(range_parts) == 1:
                return int(range_parts[0]), int(range_parts[0])
            elif len(range_parts) == 2:
                return int(range_parts[0]), int(range_parts[1]) if range_parts[1] else None
            else:
                raise ValueError(f"Invalid range format: {range_str}")

        def parse_episode_mappings(
                raw_mappings: dict[str, str]
        ) -> dict[tuple[int, int | None], list[tuple[int, int | None, int, None]]]:
            parsed: dict[tuple[int, int | None], list[tuple[int, int | None, int, None]]] = {}
            for source_range, target_range in raw_mappings.items():
                source_range_start, source_range_end = parse_range(source_range)
                target_range_parts = target_range.split("|")
                if len(target_range_parts) != 2:
                    target_ranges = target_range_parts[0]
                    step = 1
                else:
                    target_ranges, step_str = target_range_parts
                    step = int(step_str)
                target_ranges_list = [parse_range(r) for r in target_ranges.split(",")]

                parsed.setdefault((source_range_start, source_range_end), []).extend(
                    [(target_range_start, target_range_end, step, None)
                     for target_range_start, target_range_end in target_ranges_list]
                )
            return parsed

        all_mappings = json.loads(source_data.decode())
        for source_id, source_mappings in all_mappings.items():
            if source_id.startswith("anilist:"):
                anilist_id = int(source_id.split(":")[1])
                for target_id, target_mappings in source_mappings.items():
                    if not target_id.startswith("tvdb_show:"):
                        continue
                    if len(target_id.split(":")) != 3:
                        continue
                    _, tvdb_series_id, season_number = target_id.split(":")
                    tvdb_series_id = int(tvdb_series_id)
                    season_number = int(season_number.lstrip('s'))

                    series_key = (tvdb_series_id, season_number)
                    anilist_tvdb.setdefault(anilist_id, {}).setdefault(series_key, {})
                    for source_key, targets in parse_episode_mappings(target_mappings).items():
                        anilist_tvdb[anilist_id][series_key].setdefault(source_key, []).extend(targets)
            if source_id.startswith("tvdb_show:"):
                if len(source_id.split(":")) != 3:
                    continue
                _, tvdb_series_id, season_number = source_id.split(":")
                tvdb_series_id = int(tvdb_series_id)
                season_number = int(season_number.lstrip('s'))
                series_key = (tvdb_series_id, season_number)
                for target_id, target_mappings in source_mappings.items():
                    if not target_id.startswith("anilist:"):
                        continue
                    if len(target_id.split(":")) != 2:
                        continue
                    anilist_id = int(target_id.split(":")[1])

                    tvdb_anilist.setdefault(series_key, {}).setdefault(anilist_id, {})
                    for source_key, targets in parse_episode_mappings(target_mappings).items():
                        tvdb_anilist[series_key][anilist_id].setdefault(source_key, []).extend(targets)

        return anilist_tvdb, tvdb_anilist

    def _override_external_mappings(
            self,
            anilist_tvdb: dict[int, dict[tuple[int, int], dict[tuple[int, int | None],
            list[tuple[int, int | None, int, MappingOverrideMode | None]]]]],
            tvdb_anilist: dict[tuple[int, int], dict[int, dict[tuple[int, int | None],
            list[tuple[int, int | None, int, MappingOverrideMode | None]]]]],
            overrides_data: bytes
    ):
        # hot overrides are added alongside the anibridge entries, tagged ALWAYS
        try:
            raw_overrides = json.loads(overrides_data.decode()).get("mappings") or {}
            if not isinstance(raw_overrides, dict):
                raise ValueError("'mappings' is not an object")
        except (ValueError, AttributeError) as e:
            self.logger.error(f"Failed to parse hot mapping overrides: {e}")
            return

        overrides = {}
        for key, rows in raw_overrides.items():
            if key.startswith("$"):
                continue
            try:
                overrides[int(key)] = [self._parse_hot_override_row(row) for row in rows]
            except (TypeError, ValueError, KeyError) as e:
                self.logger.warning(f"Skipping invalid hot mapping override for anilist:{key}: {e}")

        for anilist_id, rows in overrides.items():
            for series_id, season_number, anilist_from, anilist_to, tvdb_from, tvdb_to, granularity in rows:
                series_key = (series_id, season_number)
                reverse_granularity = -granularity if abs(granularity) >= 2 else granularity
                anilist_tvdb.setdefault(anilist_id, {}).setdefault(series_key, {}) \
                    .setdefault((anilist_from, anilist_to), []) \
                    .append((tvdb_from, tvdb_to, granularity, MappingOverrideMode.ALWAYS))
                tvdb_anilist.setdefault(series_key, {}).setdefault(anilist_id, {}) \
                    .setdefault((tvdb_from, tvdb_to), []) \
                    .append((anilist_from, anilist_to, reverse_granularity, MappingOverrideMode.ALWAYS))

    @staticmethod
    def _parse_hot_override_row(row: dict) -> tuple[int, int, int, int | None, int, int | None, int]:
        def optional_int(value) -> int | None:
            return int(value) if value is not None else None

        granularity = int(row["gran"])
        if granularity in (0, -1):
            raise ValueError(f"invalid gran {granularity}")
        return (int(row["tvdb_series"]), int(row["tvdb_season"]),
                int(row["anilist_from"]), optional_int(row["anilist_to"]),
                int(row["tvdb_from"]), optional_int(row["tvdb_to"]),
                granularity)

    @staticmethod
    def _overrides_to_mappings(overrides: list[MappingOverride]) -> tuple[
        dict[int, dict[tuple[int, int], dict[tuple[int, int | None],
        list[tuple[int, int | None, int, MappingOverrideMode]]]]],
        dict[tuple[int, int], dict[int, dict[tuple[int, int | None],
        list[tuple[int, int | None, int, MappingOverrideMode]]]]],
    ]:
        anilist_tvdb = {}
        tvdb_anilist = {}
        for override in overrides:
            series_key = (override.tvdb_series_id, override.tvdb_season_number)
            anilist_source_key = (override.anilist_episode_number_from, override.anilist_episode_number_to)
            tvdb_source_key = (override.tvdb_episode_number_from, override.tvdb_episode_number_to)
            reverse_granularity = -override.granularity if abs(override.granularity) >= 2 else override.granularity
            tvdb_target = (override.tvdb_episode_number_from, override.tvdb_episode_number_to,
                           override.granularity, override.mode)
            anilist_target = (override.anilist_episode_number_from, override.anilist_episode_number_to,
                              reverse_granularity, override.mode)

            anilist_tvdb.setdefault(override.anilist_id, {}).setdefault(series_key, {})
            anilist_tvdb[override.anilist_id][series_key].setdefault(anilist_source_key, []).append(tvdb_target)
            tvdb_anilist.setdefault(series_key, {}).setdefault(override.anilist_id, {})
            tvdb_anilist[series_key][override.anilist_id].setdefault(tvdb_source_key, []).append(anilist_target)

        return anilist_tvdb, tvdb_anilist

    @staticmethod
    def _build_anime_relations_offset_map(source_data: bytes) -> dict[int, dict]:
        data = {
            # anilist_id
            #   relations: [{other_anilist_id, this_episode_range, other_episode_range}]
            #   referenced_by: [anilist_id]
        }
        iterator = io.StringIO(source_data.decode())
        relation_pattern = re.compile(r'^(?:\d+|[?~])\|(?:\d+|[?~])\|(?P<this_anime_id>\d+|[?~]):'
                                      r'(?P<this_range>\d+(?:-\d+)?)\s*->\s*(?:\d+|[?~])\|'
                                      r'(?:\d+|[?~])\|(?P<other_anilist_id>\d+|[?~]):'
                                      r'(?P<other_range>\d+(?:-\d+)?)(?P<repeat>!)?$')
        for line in iterator:
            if line.strip() == '::rules':
                break
        for line in iterator:
            line = line.strip()
            if line.startswith("-"):
                match = relation_pattern.match(line[1:].strip())
                if not match:
                    continue
                this_anime_id = match.group("this_anime_id")
                this_range = match.group("this_range")
                other_anilist_id = match.group("other_anilist_id")
                other_range = match.group("other_range")
                repeat = bool(match.group("repeat"))

                if this_anime_id == "?" or not this_anime_id.isdigit():
                    continue
                if other_anilist_id == "~":
                    other_anilist_id = this_anime_id
                this_anime_id = int(this_anime_id)
                data[this_anime_id] = data.get(this_anime_id, {'relations': [], 'referenced_by': set()})

                if other_anilist_id == "?" or not other_anilist_id.isdigit():
                    continue
                other_anilist_id = int(other_anilist_id)
                data[other_anilist_id] = data.get(other_anilist_id, {'relations': [], 'referenced_by': set()})

                if not this_range or not other_range:
                    continue

                if '-' in this_range:
                    this_range = tuple(map(int, this_range.split('-')))
                else:
                    this_range = (int(this_range), int(this_range))
                if '-' in other_range:
                    other_range = tuple(map(int, other_range.split('-')))
                else:
                    other_range = (int(other_range), int(other_range))

                data[this_anime_id]['relations'].append({
                    "other_anilist_id": other_anilist_id,
                    "this_episode_range": this_range,
                    "other_episode_range": other_range
                })
                if repeat:
                    data[other_anilist_id]['relations'].append({
                        "other_anilist_id": other_anilist_id,
                        "this_episode_range": this_range,
                        "other_episode_range": other_range
                    })
                if this_anime_id != other_anilist_id:
                    data[other_anilist_id]['referenced_by'].add(this_anime_id)

        return data

    @staticmethod
    def _build_anilist_episode_count_map(source_data: bytes) -> dict[int, int]:
        data = {
            # anilist_id: episode_count
        }
        iterator = io.StringIO(source_data.decode())
        pattern = re.compile(r'^(?P<id>\d+):(?P<count>\d+):(?P<expires>\d+)$')
        for line in iterator:
            match = pattern.match(line.strip())
            if not match:
                continue
            anilist_id = int(match.group('id'))
            episode_count = int(match.group('count'))
            expires_at = int(match.group('expires'))
            if expires_at < datetime.now(UTC).timestamp():
                continue
            data[anilist_id] = episode_count
        return data

    @property
    def anilist_tvdb_mappings_count(self):
        return sum(len(value) for value in self._ANILIST_TVDB_MAPPINGS.values())

    @property
    def anime_relations_offset_map_count(self):
        return len(self._ANIME_RELATIONS_OFFSET_MAP)

    async def anilist_tvdb_mappings_last_updated(self) -> datetime:
        from components.asset_component import AssetComponent
        return (await AssetComponent().get_cached_asset_object(asset_filename=self.MAPPINGS_FILENAME,
                                                               asset_type=CachedAssetType.RELATIONS)).updated_at

    async def anime_relations_offset_map_last_updated(self) -> datetime:
        from components.asset_component import AssetComponent
        return (await AssetComponent().get_cached_asset_object(asset_filename=self.OFFSET_MAP_FILENAME,
                                                               asset_type=CachedAssetType.RELATIONS)).updated_at
