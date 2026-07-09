from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest

from common.exceptions import NotFoundException
from components.api_components.mapping_api_component import MappingAPIComponent
from components.service_components.anilist_component import AnilistComponent
from components.service_components.tvdb_component import TVDBComponent
from tests.support.builders import make_anime, make_mapping_override, make_tvdb_series

_GET = "repositories.mapping_override_repo.MappingOverrideRepo.get_mapping_override"
_DELETE = "repositories.mapping_override_repo.MappingOverrideRepo.delete_mapping_override"
_GET_ANIME = "components.service_components.anilist_component.AnilistComponent.get_anime"
_GET_SERIES = "components.service_components.tvdb_component.TVDBComponent.get_series"
_AUDIT = "components.audit_log_component.AuditLogComponent.log_mapping_override_added_or_removed"


def _component() -> MappingAPIComponent:
    component = MappingAPIComponent.__new__(MappingAPIComponent)
    component._anilist_component = AnilistComponent.__new__(AnilistComponent)
    component._tvdb_component = TVDBComponent.__new__(TVDBComponent)
    return component


@dataclass
class Case:
    id: str
    exists: bool = True
    anime_resolves: bool = True  # when False, title lookup fails and titles fall back to None
    expected_exception: type[Exception] | None = None


CASES = [
    Case(id="existing override is deleted and audited with titles"),
    Case(id="title lookup failure still deletes and audits without titles", anime_resolves=False),
    Case(id="missing override -> not found", exists=False, expected_exception=NotFoundException),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_delete_mapping_override(case: Case, mocker):
    override = make_mapping_override() if case.exists else None
    mocker.patch(_GET, new_callable=AsyncMock, return_value=override)
    delete = mocker.patch(_DELETE, new_callable=AsyncMock)
    # anime None makes _get_anilist_anime raise ValidationException, exercising the title fallback branch
    mocker.patch(_GET_ANIME, new_callable=AsyncMock, return_value=make_anime(100) if case.anime_resolves else None)
    mocker.patch(_GET_SERIES, new_callable=AsyncMock, return_value=make_tvdb_series())
    audit = mocker.patch(_AUDIT, new_callable=AsyncMock)

    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            await _component().delete_mapping_override(mapping_override_id=1)
        delete.assert_not_called()
        return

    result = await _component().delete_mapping_override(mapping_override_id=1)

    assert result is None
    delete.assert_awaited_once_with(1)
    audit.assert_awaited_once()
