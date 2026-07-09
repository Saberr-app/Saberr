import asyncio

from components.service_components import BaseServiceComponent
from config import config
from dto.nyaa_item import NyaaItem, RawTorrent
from services.rss_service import RSSService

_RAW_TORRENTS = []
_RSS_LOCK = asyncio.Lock()


class RSSComponent(BaseServiceComponent):

    def __init__(self, *args, **kwargs):
        from components.operational_components.torrent_component import TorrentComponent
        super().__init__(*args, **kwargs)
        self._rss_service = RSSService()
        self._torrent_component = TorrentComponent()

    @staticmethod
    async def get_latest_raw_torrents() -> list[RawTorrent]:
        async with _RSS_LOCK:
            return _RAW_TORRENTS.copy()

    @staticmethod
    def rss_locked() -> bool:
        return _RSS_LOCK.locked()

    async def get_torrents(self, query: str | None = None,
                           release_groups: list[str] | None = None) -> list[RawTorrent]:
        async with _RSS_LOCK:
            return await self._get_torrents(query=query, release_groups=release_groups)

    async def _get_torrents(self, query: str | None = None,
                            release_groups: list[str] | None = None) -> list[RawTorrent]:
        nyaa_items = await self.get_rss_feed(query=query, release_groups=release_groups)
        raw_torrents = [self._torrent_component.init_raw_torrent(item) for item in nyaa_items]
        await self._torrent_component.populate_raw_torrents_data(
            [raw_torrent for raw_torrent in raw_torrents if raw_torrent.title_parts
             and not raw_torrent.title_parts.missing_required and not raw_torrent.is_batch_torrent]
        )
        selected_hashes, dismissed_hashes_to_reasons = await self._torrent_component.determine_torrents_candidacy(
            episode_ids=[torrent.db_episode_id for torrent in raw_torrents
                         if torrent.db_episode_id is not None
                         and torrent.db_download_id is None
                         and not torrent.discarded],
            scope_hashes={raw_torrent.nyaa_item.magnet_hash for raw_torrent in raw_torrents})
        for raw_torrent in raw_torrents:
            if raw_torrent.nyaa_item.magnet_hash in selected_hashes:
                raw_torrent.selected = True
            elif raw_torrent.nyaa_item.magnet_hash in dismissed_hashes_to_reasons:
                raw_torrent.profile_shortcomings.extend(
                    dismissed_hashes_to_reasons[raw_torrent.nyaa_item.magnet_hash]
                )
            elif raw_torrent.db_download_id:
                pass
            elif not raw_torrent.not_tracked and raw_torrent.anilist_anime_min:
                raw_torrent.superseded = True
        return raw_torrents

    async def get_rss_feed(self, query: str | None = None, release_groups: list[str] | None = None) -> list[NyaaItem]:
        feed_xml = await self._rss_service.fetch_rss(query=query, release_groups=release_groups)
        return NyaaItem.many_from_xml_string(feed_xml)

    async def consume_feed(self):
        async with _RSS_LOCK:
            raw_torrents = await self._get_torrents(release_groups=list(config.release_groups_map.keys()))
            existing_hashes = {raw_torrent.nyaa_item.magnet_hash for raw_torrent in _RAW_TORRENTS}
            new_hashes = {raw_torrent.nyaa_item.magnet_hash for raw_torrent in raw_torrents}
            if new_torrents_count := len(new_hashes - existing_hashes):
                self.logger.info(f"Consumed {new_torrents_count} new torrents from RSS feed.")
            _RAW_TORRENTS.clear()
            _RAW_TORRENTS.extend(raw_torrents)
            if not config.user_settings.auto_download:
                return
            for raw_torrent in raw_torrents:
                if raw_torrent.selected:
                    await self._torrent_component.select_torrent_for_downloading(
                        magnet_hash=raw_torrent.nyaa_item.magnet_hash
                    )
