from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from components.operational_components.tracked_anime_component import TrackedAnimeComponent
from constants import TrackedAnimeStatus

_REPO = "repositories.tracked_anime_repositories.tracked_anime_repo.TrackedAnimeRepo"
_AUDIT = "components.audit_log_component.AuditLogComponent"


@dataclass
class Case:
    id: str


CASES = [
    Case(id="sets status to ACTIVE and audits the archived->active change"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_unarchive_tracked_anime(case: Case, mocker):
    tracked = SimpleNamespace(id=5, anilist_id=50)
    mocker.patch(f"{_REPO}.get_tracked_anime_list", return_value=[tracked])
    update = mocker.patch(f"{_REPO}.update_tracked_anime")
    audit = mocker.patch(f"{_AUDIT}.log_tracked_anime_settings_change")

    await TrackedAnimeComponent().unarchive_tracked_anime(tracked_anime_ids=[5])

    update.assert_awaited_once_with(tracked_anime_id=5, status=TrackedAnimeStatus.ACTIVE)
    audit.assert_awaited_once()
    assert audit.await_args.kwargs["update_data"] == {"Status": {"old": "Archived", "new": "Active"}}
