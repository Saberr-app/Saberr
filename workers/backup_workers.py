from common.decorators import periodic_worker
from components.backup_component import BackupComponent
from utils.helpers.date_helpers import seconds_to_midnight
from workers import BaseWorkerClass


class BackupWorkers(BaseWorkerClass):
    NAME = "Backup"

    @periodic_worker(frequency=60*60*24, initial_delay=seconds_to_midnight(), listed=False)
    async def create_backup(self):
        await BackupComponent().create_backup()

    @periodic_worker(frequency=60*60*24, initial_delay=seconds_to_midnight(), listed=False)
    async def cleanup_old_backups(self):
        await BackupComponent().prune_old_backups()
