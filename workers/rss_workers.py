from app_state import downstream_healthcheck_workers
from components.service_components.rss_component import RSSComponent
from config import config
from common.decorators import require_db_session, periodic_worker
from constants import ExternalServiceCode
from workers import BaseWorkerClass


class RSSWorkers(BaseWorkerClass):
    NAME = "RSS Feeds"

    @periodic_worker(frequency=config.user_settings.rss_check_frequency, initial_delay=30)
    @require_db_session
    async def consume_rss_feeds(self):
        qbit_status = downstream_healthcheck_workers.get_status(ExternalServiceCode.QBIT)
        rss_status = downstream_healthcheck_workers.get_status(ExternalServiceCode.RSS)
        if qbit_status.checked and qbit_status.healthy and rss_status.checked and rss_status.healthy:
            await RSSComponent().consume_feed()
