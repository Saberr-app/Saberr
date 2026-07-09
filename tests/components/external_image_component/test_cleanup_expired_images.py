import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest

from components.external_image_component import ExternalImageComponent


@dataclass
class Case:
    id: str
    stale_age: timedelta   # access-time age of the file that should be removed
    fresh_age: timedelta   # access-time age of the file that should survive


CASES = [
    Case(id="removes files past CLEANUP_AFTER, keeps recent ones",
         stale_age=ExternalImageComponent.CLEANUP_AFTER + timedelta(days=1), fresh_age=timedelta()),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_cleanup_expired_images(case: Case, image_component, tmp_path):
    images = tmp_path / "images" / "anilist_media"
    images.mkdir(parents=True)
    stale, fresh = images / "stale.png", images / "fresh.png"
    stale.write_bytes(b"s")
    fresh.write_bytes(b"f")
    stale_ts = (datetime.now(UTC) - case.stale_age).timestamp()
    fresh_ts = (datetime.now(UTC) - case.fresh_age).timestamp()
    os.utime(stale, (stale_ts, stale_ts))  # cleanup keys off access time
    os.utime(fresh, (fresh_ts, fresh_ts))

    await image_component.cleanup_expired_images()

    assert not stale.exists()
    assert fresh.exists()
