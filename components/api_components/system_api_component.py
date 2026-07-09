from app_state import worker_manager, global_status
from common.context_helpers import thread_out
from common.decorators import api_component, require_db_session
from common.exceptions import ValidationException, NotFoundException
from components import BaseComponent
from components.backup_component import BackupComponent, BackupInfo
from api.schemas.system_schemas import ValidatePathRequest, Task, TaskList, SystemStats, BackupListResponse, BackupItem, \
    AppReleaseItem
from components.operational_components.tracked_anime_component import TrackedAnimeComponent
from config import config
from constants import TrackedAnimeStatus
from services.github_service import GitHubService
from system.server import get_up_since
from utils.helpers.path_helpers import is_valid_directory_path, get_disk_for_path


class SystemAPIComponent(BaseComponent):

    @api_component
    async def validate_path(self, body: ValidatePathRequest):
        if not is_valid_directory_path(path=body.path, validate_writability=body.validate_writable):
            raise ValidationException(detail=f"Directory not found or inaccessible: {body.path}")

    @require_db_session
    @api_component
    async def get_list_of_tasks(self, ref: int = 1) -> TaskList:
        return TaskList(
            ref=ref,
            tasks=[
                Task(
                    id=worker.id,
                    name=worker.name,
                    category=worker.category,
                    frequency=worker.frequency,
                    last_run=Task.WorkerLastRun(
                        run_succeeded=worker.last_run.succeeded,
                        run_time=worker.last_run.last_run_time,
                        run_duration=worker.last_run.last_run_duration,
                        run_error=worker.last_run.error,
                    ) if worker.last_run else None,
                    currently_running=worker.currently_running,
                    currently_running_since=worker.currently_running_since,
                ) for worker in worker_manager.get_worker_list()
            ]
        )

    @api_component
    async def trigger_task(self, task_id: str):
        try:
            await worker_manager.trigger_worker(worker_id=task_id)
        except ValueError:
            raise NotFoundException(detail=f"Worker with id {task_id} not found")

    @staticmethod
    def nullify_unchanged(old: TaskList | None, new: TaskList):
        old_task_map = {task.id: task for task in old.tasks} if old else {}
        new_tasks = []
        for task in new.tasks:
            if task.id not in old_task_map or task != old_task_map[task.id]:
                new_tasks.append(task)
        new.tasks = new_tasks

    @api_component
    async def get_system_stats(self) -> SystemStats:
        up_since = get_up_since()
        active_tracked_anime = await TrackedAnimeComponent().get_all_tracked_anime(statuses=[TrackedAnimeStatus.ACTIVE],
                                                                                   load_relations=False)
        import_directories = {tracked_anime.show_parent_directory for tracked_anime in active_tracked_anime}
        import_directories.add(config.user_settings.default_destination_directory)
        staging_directory = config.user_settings.staging_directory

        disk_stats: list[SystemStats.Disk] = []
        seen_mounts: set[str] = set()
        for directory in import_directories:
            if not directory:
                continue
            mount, total, used = await thread_out(get_disk_for_path, directory)
            if mount in seen_mounts:
                continue
            seen_mounts.add(mount)
            disk_stats.append(SystemStats.Disk(path=mount, name="Import destination", total=total, used=used))
        if staging_directory:
            mount, total, used = await thread_out(get_disk_for_path, staging_directory)
            disk_stats.append(SystemStats.Disk(path=mount, name="Torrent/downloads destination",
                                               total=total, used=used))

        return SystemStats(app_version=config.app_version.original_version_string,
                           up_since=up_since,
                           disk_stats=disk_stats,
                           update_available=global_status.remote_update_available)

    @api_component
    async def shutdown(self):
        from system.server import request_shutdown
        request_shutdown()

    @api_component
    async def get_list_of_backups(self) -> BackupListResponse:
        backups = await BackupComponent().list_backups()
        return BackupListResponse(backups=[self._to_backup_item(backup) for backup in backups])

    @api_component
    async def create_backup(self) -> BackupItem:
        return self._to_backup_item(await BackupComponent().create_backup(user_initiated=True))

    @api_component
    async def request_backup_restore(self, filename: str):
        await BackupComponent().create_backup()
        await BackupComponent().mark_backup_for_restoration(filename=filename)

    @api_component
    async def delete_backup(self, filename: str):
        await BackupComponent().delete_backup(filename=filename)

    @api_component
    async def get_current_app_release(self) -> AppReleaseItem:
        current_release = await GitHubService().get_release(tag=f"v{config.app_version.original_version_string}")
        return AppReleaseItem(
            web_link=current_release["html_url"],
            current_version=config.app_version.original_version_string,
            version=current_release["tag_name"].lstrip("v"),
            name=current_release.get("name") or current_release["tag_name"],
            body=current_release.get("body"),
            published_at=current_release["published_at"]
        )

    @api_component
    async def get_latest_app_release(self) -> AppReleaseItem:
        latest_release = await GitHubService().get_latest_release()
        return AppReleaseItem(
            web_link=latest_release["html_url"],
            current_version=config.app_version.original_version_string,
            version=latest_release["tag_name"].lstrip("v"),
            name=latest_release.get("name") or latest_release["tag_name"],
            body=latest_release.get("body"),
            published_at=latest_release["published_at"]
        )

    @staticmethod
    def _to_backup_item(backup: BackupInfo) -> BackupItem:
        return BackupItem(
            filename=backup.filename,
            location=backup.path,
            app_version=backup.app_version,
            size=backup.size_bytes,
            created_at=backup.created_at,
            can_restore=backup.can_restore,
        )
