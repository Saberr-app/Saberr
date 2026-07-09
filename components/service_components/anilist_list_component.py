import json
from collections import defaultdict
from datetime import datetime, UTC

from common.db import get_session
from common.exceptions import (AnilistNotAuthenticatedException, ExternalServiceException,
                               AnilistUnauthorizedException, AnilistNotFoundException)
from components.service_components import BaseServiceComponent
from config import config
from constants import AnilistAnimeUserStatus, AuditLogCode, SettingsCode
from dto.anilist import AnilistUserList, AnilistUserListEntry, AnilistDate
from system import UNSET
from app_state import global_status
from repositories.cache_repositories.anilist_anime_repo import AnilistAnimeRepo
from repositories.cache_repositories.anilist_list_item_repo import AnilistListItemRepo
from services.anilist_service import AnilistService


class AnilistListComponent(BaseServiceComponent):

    def __init__(self, *args, **kwargs):
        from components.settings_component import SettingsComponent
        super().__init__(*args, **kwargs)
        self._anilist_service = AnilistService()
        self._settings_component = SettingsComponent()

    async def get_user_anime_list(self, force_fetch: bool = False,
                                  fetch_full_anime_data: bool = False) -> AnilistUserList:
        if not config.user_settings.anilist_user_token:
            raise AnilistNotAuthenticatedException()
        if force_fetch:
            return await self.fetch_user_anime_list(fetch_full_anime_data=fetch_full_anime_data)
        anilist_list_items = await AnilistListItemRepo(get_session()).get_anilist_list()
        return AnilistUserList.from_list_of_orm(anilist_list_items)

    async def fetch_user_anime_list(self, fetch_full_anime_data: bool = False) -> AnilistUserList:
        # fetch_full_anime_data must be avoided in all cases where possible
        #  due to the massive response size and timeout risks (+3 MB response for 1k items list),
        #  currently only used for the very first fetch upon user auth to anilist and GET list API
        try:
            anime_list_data = await self._anilist_service.get_user_anime_list(
                username=config.user_settings.anilist_username,
                fetch_full_anime_data=fetch_full_anime_data
            )
        except ExternalServiceException as e:
            if e.status_code in (401, 403):
                raise AnilistUnauthorizedException() from e
            raise e

        list_items: list[dict] = []
        for list_data in anime_list_data:
            if list_data["isCustomList"]:
                continue
            list_items.extend(list_data.get('entries', []))

        if fetch_full_anime_data:
            anime_data = []
            for list_item in list_items:
                anime_data.append(list_item.pop('media'))

            await AnilistAnimeRepo(get_session()).bulk_upsert_anilist_anime(
                data_list=[
                    {
                        "anilist_id": anime["id"],
                        "data": anime,
                    } for anime in anime_data
                ]
            )

        deleted = await AnilistListItemRepo(get_session()).delete_all(
            exclude_anilist_ids={list_item['mediaId'] for list_item in list_items}
        )
        upserted = await AnilistListItemRepo(get_session()).bulk_upsert_anilist_list_item(
            data_list=[
                {
                    'anilist_id': list_item['mediaId'],
                    'data': list_item
                } for list_item in list_items
            ]
        )
        await self._settings_component.update_settings(
            {SettingsCode.ANILIST_USER_DATA: await self._anilist_service.get_user_data()}
        )

        self.logger.debug(f"Refreshed user anime list: {deleted=} {upserted=}.")
        # await self._audit_log_component.log_user_anime_list_refreshed()  # spammy
        if deleted or upserted:
            global_status.anime_list_refreshed()
        return AnilistUserList.from_list_of_dict(data=list_items)

    async def get_user_anime_list_entry(self, anilist_id: int,
                                        force_fetch: bool = False) -> AnilistUserListEntry | None:
        if not config.user_settings.anilist_user_token:
            raise AnilistNotAuthenticatedException()

        entry = await AnilistListItemRepo(get_session()).get_anilist_list_item(anilist_id=anilist_id)
        entry_data = entry.data if entry else None
        if force_fetch:
            try:
                entry_data = await self._anilist_service.get_user_anime_list_entry(
                    anilist_id=anilist_id,
                    fetch_full_anime_data=True
                )
            except ExternalServiceException as e:
                if e.status_code in (401, 403):
                    raise AnilistUnauthorizedException() from e
                raise e

            if not entry_data:
                return None

            anime_data = entry_data.pop('media')
            await AnilistAnimeRepo(get_session()).bulk_upsert_anilist_anime(
                data_list=[{"anilist_id": anime_data["id"], "data": anime_data}]
            )

        if not entry_data:
            return None
        return AnilistUserListEntry.from_dict(entry_data)

    # noinspection PyMethodMayBeStatic
    async def get_user_anime_list_entries(self, anilist_ids: list[int]) -> list[AnilistUserListEntry]:
        if not config.user_settings.anilist_user_token:
            raise AnilistNotAuthenticatedException()

        entries = await AnilistListItemRepo(get_session()).get_anilist_list_items(anilist_ids=anilist_ids)
        return [AnilistUserListEntry.from_dict(entry.data) for entry in entries]

    # noinspection PyMethodMayBeStatic
    async def delete_user_anime_list(self) -> None:
        await AnilistListItemRepo(get_session()).delete_all()

    async def update_user_list_entry(self, anilist_anime_id: int,
                                     status: AnilistAnimeUserStatus | None = None,
                                     progress: int | None = None,
                                     score: int | float | None = None,
                                     repeat_count: int | None = None,
                                     started_at: AnilistDate | None = None,
                                     completed_at: AnilistDate | None = None,
                                     is_private: bool | None = None,
                                     notes: str | None = UNSET) -> AnilistUserListEntry:
        if not config.user_settings.anilist_user_token:
            raise AnilistNotAuthenticatedException()
        self.logger.debug(f"Updating user anime list entry: {anilist_anime_id=}, {status=}, {score=},"
                          f" {repeat_count=}, {started_at=}, {completed_at=}, {is_private=}, {notes=}")
        existing_data = await AnilistListItemRepo(get_session()).get_anilist_list_item(anilist_id=anilist_anime_id)
        if existing_data:
            existing_data = existing_data.data
        updated_entry_data = await self._anilist_service.update_anime_list_entry(
            anilist_anime_id=anilist_anime_id,
            status=status,
            progress=progress,
            score=score,
            repeat=repeat_count,
            started_at=started_at,
            completed_at=completed_at,
            private=is_private,
            notes=notes,
        )

        await AnilistListItemRepo(get_session()).upsert_anilist_list_item(anilist_id=anilist_anime_id,
                                                                          data=updated_entry_data)
        if not existing_data:
            await self._audit_log_component.log_user_added_or_removed_anime_from_list(
                code=AuditLogCode.ANILIST_ANIME_ADDED,
                anime_id=anilist_anime_id,
                user_data=updated_entry_data
            )
        else:
            changed_data = {k: {"old": existing_data[k], "new": updated_entry_data[k]}
                            for k in existing_data if existing_data[k] != updated_entry_data[k]}
            if changed_data:
                await self._audit_log_component.log_user_updated_anime_list_entry(
                    anime_id=anilist_anime_id,
                    updated_data=changed_data,
                )

        return AnilistUserListEntry.from_dict(updated_entry_data)

    async def update_user_list_entries(self, anilist_ids: list[int],
                                       status: AnilistAnimeUserStatus | None = None,
                                       score: int | float | None = None) -> list[AnilistUserListEntry]:
        if not config.user_settings.anilist_user_token:
            raise AnilistNotAuthenticatedException()
        self.logger.debug(f"Updating user anime list entries: {anilist_ids=}, {status=}, {score=}")
        user_list = await self.get_user_anime_list()
        new_anilist_ids = {anilist_id for anilist_id in anilist_ids if not user_list.get_entry_by_anime_id(anilist_id)}

        anilist_id_with_started_at_list = []
        anilist_id_with_completed_list = []
        anilist_id_list = []
        repeat_count_anilist_ids_map = defaultdict(list)

        for anilist_id in anilist_ids:
            existing_entry = user_list.get_entry_by_anime_id(anilist_id)
            if status:
                if status == AnilistAnimeUserStatus.CURRENT \
                        and existing_entry and existing_entry.started_at_empty():
                    anilist_id_with_started_at_list.append(anilist_id)
                elif status == AnilistAnimeUserStatus.COMPLETED:
                    if existing_entry and existing_entry.completed_at_empty():
                        anilist_id_with_completed_list.append(anilist_id)
                    elif existing_entry and existing_entry.status == AnilistAnimeUserStatus.REPEATING:
                        repeat_count_anilist_ids_map[existing_entry.repeat_count + 1].append(anilist_id)
                    else:
                        anilist_id_list.append(anilist_id)
                else:
                    anilist_id_list.append(anilist_id)
            else:
                anilist_id_list.append(anilist_id)

        completed_at = started_at = datetime.now(UTC)

        update_data_list = []
        update_data_list.extend(await self._anilist_service.batch_update_anime_list_entries(
            anilist_anime_ids=anilist_id_with_started_at_list,
            status=status,
            score=score,
            started_at=started_at
        ))
        update_data_list.extend(await self._anilist_service.batch_update_anime_list_entries(
            anilist_anime_ids=anilist_id_with_completed_list,
            status=status,
            score=score,
            completed_at=completed_at
        ))
        update_data_list.extend(await self._anilist_service.batch_update_anime_list_entries(
            anilist_anime_ids=anilist_id_list,
            status=status,
            score=score
        ))
        for repeat_count, repeat_anilist_ids in repeat_count_anilist_ids_map.items():
            update_data_list.extend(
                await self._anilist_service.batch_update_anime_list_entries(anilist_anime_ids=repeat_anilist_ids,
                                                                            status=status,
                                                                            score=score,
                                                                            repeat=repeat_count)
            )

        diff_groups: dict[str, dict] = {}
        for updated_entry_data in update_data_list:
            anilist_id = updated_entry_data["mediaId"]
            if anilist_id in new_anilist_ids:
                continue
            existing_data = user_list.get_entry_by_anime_id(anilist_id).raw_data
            changed_data = {k: {"old": existing_data[k], "new": updated_entry_data[k]}
                            for k in existing_data if existing_data[k] != updated_entry_data[k]}
            if not changed_data:
                continue
            group = diff_groups.setdefault(json.dumps(changed_data, sort_keys=True),
                                           {"changed_data": changed_data, "anime_ids": []})
            group["anime_ids"].append(anilist_id)

        await AnilistListItemRepo(get_session()).bulk_upsert_anilist_list_item(
            data_list=[
                {
                    "anilist_id": updated_entry_data_["mediaId"],
                    "data": updated_entry_data_
                } for updated_entry_data_ in update_data_list
            ]
        )
        if new_anilist_ids:
            await self._audit_log_component.log_user_batch_added_or_removed_anime_from_list(
                code=AuditLogCode.BATCH_ANILIST_ANIME_ADDED,
                anime_ids=list(new_anilist_ids),
                user_data={"status": status.value}
            )
        for group_ in diff_groups.values():
            await self._audit_log_component.log_batch_user_updated_anime_list_entry(
                anime_ids=group_["anime_ids"],
                updated_data=group_["changed_data"],
            )

        return [AnilistUserListEntry.from_dict(updated_entry_data) for updated_entry_data in update_data_list]

    async def delete_user_list_entry(self, anilist_anime_id: int):
        if not config.user_settings.anilist_user_token:
            raise AnilistNotAuthenticatedException()
        self.logger.debug(f"Deleting user anime list entry: {anilist_anime_id=}")

        list_item = await AnilistListItemRepo(get_session()).get_anilist_list_item(anilist_id=anilist_anime_id)
        if not list_item:
            raise AnilistNotFoundException(f"Anime list item with anilist_id {anilist_anime_id} not found")
        entry = AnilistUserListEntry.from_dict(list_item.data)

        deleted = await self._anilist_service.delete_anime_list_entry(list_entry_id=entry.entry_id)

        if deleted:
            await AnilistListItemRepo(get_session()).delete_list_item(anilist_id=anilist_anime_id)
            await self._audit_log_component.log_user_added_or_removed_anime_from_list(
                code=AuditLogCode.ANILIST_ANIME_DELETED,
                anime_id=anilist_anime_id,
                user_data=entry.raw_data
            )

    async def delete_user_list_entries(self, anilist_ids: list[int]):
        if not config.user_settings.anilist_user_token:
            raise AnilistNotAuthenticatedException()
        self.logger.debug(f"Deleting user anime list entries: {anilist_ids=}")
        user_list = await self.get_user_anime_list()
        list_entry_ids = [user_list.get_entry_by_anime_id(anilist_id).entry_id for anilist_id in anilist_ids]
        await self._anilist_service.batch_delete_anime_list_entries(list_entry_ids=list_entry_ids)

        await AnilistListItemRepo(get_session()).delete_list_items(anilist_ids=anilist_ids)
        await self._audit_log_component.log_user_batch_added_or_removed_anime_from_list(
            code=AuditLogCode.BATCH_ANILIST_ANIME_DELETED,
            anime_ids=anilist_ids
        )
