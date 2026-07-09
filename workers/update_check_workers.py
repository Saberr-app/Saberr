from common.decorators import periodic_worker
from config import config
from dto.app_version import AppVersion
from services.github_service import GitHubService
from workers import BaseWorkerClass


class UpdateCheckWorkers(BaseWorkerClass):
    NAME = "Update check"

    def __init__(self):
        super().__init__()
        self._github_service = GitHubService()

    @periodic_worker(frequency=60*60*12, initial_delay=90, listed=False)
    async def check_for_update(self):
        from app_state import global_status
        try:
            latest_release = await self._github_service.get_latest_release()
        except Exception as e:
            self._logger.debug(f"Failed to check for app updates: {e}")
            return
        latest_version = AppVersion.from_string(latest_release["tag_name"].lstrip("v"))
        if latest_version > config.app_version:
            global_status.update_available()
