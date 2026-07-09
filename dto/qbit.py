from dataclasses import dataclass

from constants import QBITTORRENT_ERROR_STATES, QBITTORRENT_UNFINISHED_STATES
from utils.helpers.path_helpers import get_local_path_from_remote


@dataclass
class QBitTorrent:
    amount_left: int  # in bytes, 0 if not yet known
    eta: int | None  # in seconds, 8640000 (100 days) if unknown
    hash: str
    name: str  # equals hash if name not yet known
    progress: float  # between 0 and 1
    save_path: str  # parent directory
    content_path: str | None
    state: str
    size: int  # in bytes, 0 if not yet known

    original_save_path: str
    original_content_path: str | None

    @classmethod
    def from_dict(cls, data: dict, remote_path_mapping: tuple[str, str] | None) -> 'QBitTorrent':
        save_path = get_local_path_from_remote(data['save_path'],
                                               remote_path_mapping) if data['save_path'] else None
        content_path = get_local_path_from_remote(data['content_path'],
                                                  remote_path_mapping) if data.get('content_path') else None
        return cls(
            amount_left=data.get('amount_left', 0),
            eta=data.get('eta') if data.get('eta') != 8640000 else None,
            hash=data['hash'],
            name=data['name'],
            progress=data['progress'],
            save_path=save_path,
            content_path=content_path,
            state=data['state'],
            size=data.get('size', 0),
            original_save_path=data['save_path'],
            original_content_path=data.get('content_path'),
        )

    @classmethod
    def many_from_dict(cls, torrents: list[dict], remote_path_mapping: tuple[str, str] | None) -> list['QBitTorrent']:
        if not torrents:
            return []
        return [cls.from_dict(t, remote_path_mapping) for t in torrents]

    def is_finished(self) -> bool:
        return self.state not in QBITTORRENT_UNFINISHED_STATES

    def has_error(self) -> bool:
        return self.state in QBITTORRENT_ERROR_STATES
