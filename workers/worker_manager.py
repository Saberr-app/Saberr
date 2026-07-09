import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, UTC
from types import coroutine

from common.context_helpers import create_isolated_task
from common.exceptions import WorkerAlreadyRunningException


class WorkerManagerService:
    RETRY_DELAY = 600

    def __init__(self):
        self._worker_queue: asyncio.PriorityQueue = None  # type: ignore
        self._worker_run_details_map: dict[str, WorkerRunDetails] = {}
        self.__worker_task = None
        self.__workers_registered = False
        self.logger = logging.getLogger(self.__class__.__name__)

    async def run(self):
        await self.register_workers()
        self.__worker_task = create_isolated_task(self._run())

    async def stop(self):
        if self.__worker_task:
            self.__worker_task.cancel()
            try:
                await self.__worker_task
            except asyncio.CancelledError:
                pass
            self.logger.info("WorkerManagerService stopped.")

    async def _run(self):
        self.logger.info("WorkerManagerService has started.")
        while True:
            last_handled_worker_item = None
            while (worker_item := await self._worker_queue.get()).next_run <= datetime.now(UTC).timestamp():
                create_isolated_task(self.start_worker(worker_item=worker_item))
                self._worker_queue.task_done()
                last_handled_worker_item = worker_item
            if worker_item and worker_item != last_handled_worker_item:
                await self._worker_queue.put(worker_item)
            await asyncio.sleep(0.5)

    async def add_worker(self,
                         worker_callable: coroutine,
                         worker_name: str,
                         next_run: float,
                         run_frequency: int,
                         requeue: bool = True):
        if not next_run:
            self.logger.info(f"Worker {worker_name} will not be added to the queue "
                             f"as it is not scheduled to run again.")
            return
        await self._worker_queue.put(WorkerItem(next_run=next_run,
                                                worker_callable=worker_callable,
                                                worker_name=worker_name,
                                                run_frequency=run_frequency,
                                                requeue=requeue))
        if worker_callable.worker_data["id"] not in self._worker_run_details_map:
            self._worker_run_details_map[worker_callable.worker_data["id"]] = WorkerRunDetails(
                callable=worker_callable,
                lock=asyncio.Lock()
            )

    async def start_worker(self, worker_item: 'WorkerItem'):
        async with self._worker_run_details_map[worker_item.worker_callable.worker_data["id"]].lock:
            run_succeeded = True
            failure_reason = None
            wait_time = worker_item.run_frequency
            run_time = datetime.now(UTC)
            worker_details = self._worker_run_details_map[worker_item.worker_callable.worker_data["id"]]
            self.logger.debug(f"Running worker {worker_item.worker_name}.")

            try:
                worker_details.currently_running = True
                worker_details.currently_running_since = run_time
                await worker_item.worker_callable()
            except Exception as e:
                run_succeeded = False
                failure_reason = str(e)
                wait_time = self.RETRY_DELAY
                self.logger.warning(f"Error while running worker {worker_item.worker_name}: {e}", exc_info=True)
            finally:
                worker_details.currently_running = False
                worker_details.currently_running_since = None
                worker_details.last_run = WorkerLastRun(
                    succeeded=run_succeeded,
                    last_run_time=run_time,
                    last_run_duration=int(datetime.now(UTC).timestamp() - run_time.timestamp()),
                    error=failure_reason
                )
                if worker_item.requeue:
                    await self.add_worker(worker_callable=worker_item.worker_callable,
                                          worker_name=worker_item.worker_name,
                                          next_run=run_time.timestamp() + wait_time,
                                          run_frequency=worker_item.run_frequency)

    async def register_workers(self):
        """
        This method will be called on startup to register all workers with worker decorators.
        """
        from app_state import downstream_healthcheck_workers
        from workers.cleanup_workers import CleanupWorkers
        from workers.rss_workers import RSSWorkers
        from workers.notification_workers import NotificationWorkers
        from workers.download_workers import DownloadWorkers
        from workers.backup_workers import BackupWorkers
        from workers.update_check_workers import UpdateCheckWorkers

        if self.__workers_registered:
            self.logger.warning("Workers have already been registered. Skipping register call.")
            return
        self._worker_queue = asyncio.PriorityQueue()

        cleanup_workers = CleanupWorkers()
        rss_workers = RSSWorkers()
        notification_workers = NotificationWorkers()
        download_workers = DownloadWorkers()
        backup_workers = BackupWorkers()
        update_workers = UpdateCheckWorkers()

        worker_callables = [
            # downstream healthcheck
            downstream_healthcheck_workers.poll_downstream_status,
            # cleanup/refresh
            cleanup_workers.cleanup_in_memory_caches,
            cleanup_workers.refresh_anime_relations_cache,
            cleanup_workers.refresh_stale_db_data,
            cleanup_workers.cleanup_db_and_disk_cache,
            cleanup_workers.refresh_anime_user_lists,
            # rss feed
            rss_workers.consume_rss_feeds,
            # notifications
            notification_workers.process_notifications,
            # processing
            download_workers.post_download_processing,
            download_workers.stuck_check,
            # backup
            backup_workers.create_backup,
            backup_workers.cleanup_old_backups,
            # updates
            update_workers.check_for_update
        ]

        for worker_callable in worker_callables:
            await self.add_worker(
                worker_callable=worker_callable,
                worker_name=worker_callable.worker_data['name'],
                next_run=datetime.now(UTC).timestamp() + worker_callable.worker_data['initial_delay'],
                run_frequency=worker_callable.worker_data.get('frequency')
            )
        worker_list_str = "\n• ".join([worker_callable.worker_data['name'] for worker_callable in worker_callables])
        self.logger.info(f"Registered {len(worker_callables)} workers:\n• {worker_list_str}")
        self.__workers_registered = True

    def get_worker_list(self) -> list['WorkerDetails']:
        worker_list = []
        for id_, worker_run_details in self._worker_run_details_map.items():
            if not worker_run_details.callable.worker_data["listed"]:
                continue
            worker_details = WorkerDetails(id=id_,
                                           name=worker_run_details.callable.worker_data['name'],
                                           category=worker_run_details.callable.__self__.NAME,
                                           frequency=worker_run_details.callable.worker_data.get('frequency'),
                                           last_run=worker_run_details.last_run,
                                           currently_running=worker_run_details.currently_running,
                                           currently_running_since=worker_run_details.currently_running_since)
            worker_list.append(worker_details)
        return sorted(worker_list, key=lambda x: x.category)

    def get_worker_details(self, worker_id: str) -> 'WorkerDetails | None':
        if worker_id not in self._worker_run_details_map:
            return None
        worker_run_details = self._worker_run_details_map[worker_id]
        return WorkerDetails(id=worker_id,
                             name=worker_run_details.callable.worker_data['name'],
                             category=worker_run_details.callable.__self__.NAME,
                             frequency=worker_run_details.callable.worker_data.get('frequency'),
                             last_run=worker_run_details.last_run,
                             currently_running=worker_run_details.currently_running,
                             currently_running_since=worker_run_details.currently_running_since)

    def get_worker_next_run(self, worker_id: str) -> datetime | None:
        future_run_stamps = []
        for worker_item in self._worker_queue._queue:  # noqa
            if worker_item.worker_callable.worker_data["id"] == worker_id:
                future_run_stamps.append(worker_item.next_run)
        future_run_stamps.sort()
        if future_run_stamps:
            return datetime.fromtimestamp(future_run_stamps[0], UTC)
        else:
            return None

    async def trigger_worker(self, worker_id: str):
        if worker_id not in self._worker_run_details_map:
            raise ValueError(f"Worker with id {worker_id} not found.")
        elif self._worker_run_details_map[worker_id].currently_running:
            raise WorkerAlreadyRunningException(f"Worker is already running.")
        worker_callable = self._worker_run_details_map[worker_id].callable
        await self.add_worker(worker_callable=worker_callable,
                              worker_name=worker_callable.worker_data['name'],
                              next_run=datetime.now(UTC).timestamp(),
                              run_frequency=worker_callable.worker_data.get('frequency'),
                              requeue=False)


@dataclass
class WorkerItem:
    next_run: float
    worker_callable: coroutine
    worker_name: str
    run_frequency: int | None
    requeue: bool = True  # false for manually triggered

    def __lt__(self, other):
        return self.next_run < other.next_run

    def __gt__(self, other):
        return self.next_run > other.next_run


@dataclass 
class WorkerLastRun:
    succeeded: bool
    last_run_time: datetime
    last_run_duration: int
    error: str | None = None


@dataclass
class WorkerRunDetails:
    callable: coroutine
    lock: asyncio.Lock
    last_run: WorkerLastRun | None = None
    currently_running: bool = False
    currently_running_since: datetime | None = None


@dataclass
class WorkerDetails:
    id: str
    name: str
    category: str
    frequency: int | None
    last_run: WorkerLastRun | None = None
    currently_running: bool = False
    currently_running_since: datetime | None = None
