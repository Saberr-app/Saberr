from dataclasses import dataclass, field
from datetime import datetime, UTC

from common.db import add_post_commit_action


@dataclass
class GlobalStatus:
    settings_last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))
    tracked_anime_last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))
    anime_list_last_refreshed: datetime = field(default_factory=lambda: datetime.now(UTC))
    services_status_last_changed: datetime = field(default_factory=lambda: datetime.now(UTC))
    download_last_added: datetime = field(default_factory=lambda: datetime.now(UTC))
    remote_update_available: bool = False

    unread_notification_count = 0
    unread_error_notification_count = 0
    notification_count_stale = True

    def settings_updated(self):
        add_post_commit_action(setattr, self, 'settings_last_updated', datetime.now(UTC))

    def tracked_anime_updated(self):
        add_post_commit_action(setattr, self, 'tracked_anime_last_updated', datetime.now(UTC))

    def anime_list_refreshed(self):
        add_post_commit_action(setattr, self, 'anime_list_last_refreshed', datetime.now(UTC))

    def services_status_changed(self):
        add_post_commit_action(setattr, self, 'services_status_last_changed', datetime.now(UTC))

    def notifications_updated(self):
        add_post_commit_action(setattr, self, 'notification_count_stale', True)

    def download_added(self):
        add_post_commit_action(setattr, self, 'download_last_added', datetime.now(UTC))

    def update_available(self):
        self.remote_update_available = True
