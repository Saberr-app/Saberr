import asyncio
from collections import defaultdict
from datetime import datetime, UTC, timedelta
from typing import Iterable

from common.db import get_session
from components.service_components import BaseServiceComponent
from constants import AnilistAnimeStatus
from dto.anilist import AnilistAiringScheduleItem
from repositories.cache_repositories.anilist_anime_airing_schedule_repo import AnilistAnimeAiringScheduleRepo
from services.anilist_service import AnilistService


class AnilistAiringScheduleComponent(BaseServiceComponent):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._anilist_service = AnilistService()

    async def get_future_anime_schedule_records_map(self,
                                                    anilist_id_status_map: dict[int, AnilistAnimeStatus | None],
                                                    filter_out_past: bool = True,
                                                    force_fetch: bool = False
                                                    ) -> dict[int, list[AnilistAiringScheduleItem]]:
        anilist_id_schedule_records_map = defaultdict(list)
        anilist_ids_to_lookup = set()
        for anilist_id, status in anilist_id_status_map.items():
            if status and status in [AnilistAnimeStatus.FINISHED, AnilistAnimeStatus.CANCELLED]:
                anilist_id_schedule_records_map[anilist_id] = []
            else:
                anilist_ids_to_lookup.add(anilist_id)

        if not anilist_ids_to_lookup:
            return anilist_id_schedule_records_map

        if not force_fetch:
            db_records = await AnilistAnimeAiringScheduleRepo(get_session()).get_anilist_anime_airing_schedule_list(
                anilist_ids_to_lookup, minimum_airing_at=int(datetime.now(UTC).timestamp()) if filter_out_past else None
            )
            for db_record in db_records:
                anilist_id_schedule_records_map[db_record.anilist_id].append(
                    AnilistAiringScheduleItem(
                        anilist_id=db_record.anilist_id,
                        episode=db_record.episode,
                        airing_at=db_record.airing_at
                    )
                )

        anime_airing_schedule_items = await self.fetch_anime_airing_schedules(
            anilist_ids_to_lookup - set(anilist_id_schedule_records_map)
        )
        for anime_airing_schedule_item in anime_airing_schedule_items:
            anilist_id_schedule_records_map[anime_airing_schedule_item.anilist_id].append(anime_airing_schedule_item)

        return anilist_id_schedule_records_map

    async def fetch_anime_airing_schedules(self,
                                           anilist_anime_ids: Iterable[int]) -> list[AnilistAiringScheduleItem]:
        if not anilist_anime_ids:
            return []
        anilist_anime_ids = list(set(anilist_anime_ids))
        schedule_tuples = []
        anilist_id_episode_number_set = set()
        for i in range(0, len(anilist_anime_ids), 50):
            anime_records = await self._anilist_service.get_future_airing_schedule(
                anilist_anime_ids=anilist_anime_ids[i:i + 50],
            )
            for anime in anime_records:
                for node in anime["airingSchedule"]["nodes"]:
                    schedule_tuples.append((anime['id'], node['episode'], node['airingAt']))
                    anilist_id_episode_number_set.add((anime['id'], node['episode']))
            if i + 50 < len(anilist_anime_ids):
                await asyncio.sleep(0.5)

        # clean up stale episodes
        future_records = await AnilistAnimeAiringScheduleRepo(get_session()).get_anilist_anime_airing_schedule_list(
            anilist_anime_ids, minimum_airing_at=int(datetime.now(UTC).timestamp())
        )
        await AnilistAnimeAiringScheduleRepo(get_session()).delete_by_ids(ids=[r.id for r in future_records
                                                                               if (r.anilist_id, r.episode)
                                                                               not in anilist_id_episode_number_set])

        await AnilistAnimeAiringScheduleRepo(get_session()).bulk_upsert_anilist_anime_airing_schedule(
            data_list=[
                {
                    "anilist_id": anilist_id,
                    "episode": episode,
                    "airing_at": airing_at
                }
                for anilist_id, episode, airing_at in schedule_tuples
            ]
        )

        return [
            AnilistAiringScheduleItem(
                anilist_id=anilist_id,
                episode=episode,
                airing_at=airing_at
            ) for anilist_id, episode, airing_at in schedule_tuples
        ]

    async def get_airing_schedules_in_range(self,
                                            from_date: datetime,
                                            to_date: datetime,
                                            anilist_anime_ids: Iterable[int],
                                            force_fetch: bool = False) -> dict[int, list[AnilistAiringScheduleItem]]:
        if (to_date - from_date).days > 31:
            raise ValueError("from_date and to_date must be within 31 days")
        from_date = from_date.astimezone(tz=UTC)
        to_date = to_date.astimezone(tz=UTC) - timedelta(seconds=1)

        months = list({datetime(year=from_date.year, month=from_date.month, day=1, tzinfo=UTC),
                       datetime(year=to_date.year, month=to_date.month, day=1, tzinfo=UTC)})
        if (to_date - from_date).days <= 7:
            either_month_works = True
        elif len(months) == 2:
            either_month_works = False
        else:
            either_month_works = True

        db_records = await AnilistAnimeAiringScheduleRepo(get_session()).get_monthly_airing_schedules(
            anilist_ids=anilist_anime_ids, months=months
        )
        anilist_id_db_records = defaultdict(list)
        for db_record in db_records:
            anilist_id_db_records[db_record.anilist_id].append(db_record)

        anilist_id_schedule_records_map = {}
        month_missing_anilist_ids_map = defaultdict(set)
        if not force_fetch:
            for anilist_id in anilist_anime_ids:
                db_records = anilist_id_db_records.get(anilist_id, [])
                if not db_records:
                    for month in months[:1 if either_month_works else 2]:
                        month_missing_anilist_ids_map[month].add(anilist_id)
                    continue
                for db_record in db_records:
                    anilist_id_schedule_records_map.setdefault(db_record.anilist_id, set()).update(
                        {
                            AnilistAiringScheduleItem(
                                anilist_id=anilist_id,
                                episode=db_record_data_entry["episode"],
                                airing_at=db_record_data_entry["airingAt"]
                            ) for db_record_data_entry in db_record.data
                            if db_record_data_entry["airingAt"] in range(int(from_date.timestamp()),
                                                                         int(to_date.timestamp()) + 1)
                        }
                    )
                if either_month_works or len(months) == len(db_records):
                    continue
                # now we're at 1 db record, 2 months, both required
                for month in months:
                    if month not in {db_record.month for db_record in db_records}:
                        month_missing_anilist_ids_map[month].add(anilist_id)
                        break
        else:
            for month in months:
                month_missing_anilist_ids_map[month] = set(anilist_anime_ids)

        for month, missing_anilist_ids in month_missing_anilist_ids_map.items():
            fetch_from_datetime = month - timedelta(days=8)  # 1 week plus a day to account for user timezone, I think
            to_month, to_year = month.month + 1, month.year
            if to_month > 12:
                to_month = 1
                to_year += 1
            fetch_to_datetime = month.replace(year=to_year, month=to_month) + timedelta(days=8)

            fetched_records = []
            for page in range(1, 30):  # cap at 30 although unlikely to reach this much (typically 12 for 100 airing)
                fetched_airing_schedule_items = await self._anilist_service.get_airing_schedule(
                    anilist_anime_ids=list(missing_anilist_ids),
                    datetime_greater_than=fetch_from_datetime - timedelta(seconds=1),
                    datetime_less_than=fetch_to_datetime,
                    page=page
                )
                fetched_records.extend(fetched_airing_schedule_items)
                if len(fetched_airing_schedule_items) < 50:
                    break
                await asyncio.sleep(1.5)
            anilist_id_schedule_records_map_ = defaultdict(list)
            for fetched_record in fetched_records:
                anilist_id_schedule_records_map_[fetched_record["mediaId"]].append({
                    "episode": fetched_record["episode"],
                    "airingAt": fetched_record["airingAt"]
                })
                if fetched_record["airingAt"] in range(int(from_date.timestamp()), int(to_date.timestamp()) + 1):
                    anilist_id_schedule_records_map.setdefault(fetched_record["mediaId"], set()).add(
                        AnilistAiringScheduleItem(
                            anilist_id=fetched_record["mediaId"],
                            episode=fetched_record["episode"],
                            airing_at=fetched_record["airingAt"]
                        )
                    )
            for anilist_id in (missing_anilist_ids - set(anilist_id_schedule_records_map_)):
                anilist_id_schedule_records_map_[anilist_id] = []
            await AnilistAnimeAiringScheduleRepo(get_session()).bulk_upsert_anilist_anime_monthly_airing_schedule(
                [
                    {
                        "anilist_id": anilist_id,
                        "month": month,
                        "data": records
                    } for anilist_id, records in anilist_id_schedule_records_map_.items()
                ]
            )

        return {anilist_id: sorted(schedules, key=lambda x: x.airing_at)
                for anilist_id, schedules in anilist_id_schedule_records_map.items()}
