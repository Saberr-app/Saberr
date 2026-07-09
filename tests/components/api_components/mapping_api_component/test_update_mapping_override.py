from dataclasses import dataclass, field
from unittest.mock import AsyncMock

import pytest

from common.exceptions import NotFoundException, ValidationException
from components.api_components.mapping_api_component import MappingAPIComponent
from components.service_components.anilist_component import AnilistComponent
from components.service_components.tvdb_component import TVDBComponent
from tests.support.builders import make_anime, make_mapping_override, make_mapping_request, make_tvdb_series

_GET = "repositories.mapping_override_repo.MappingOverrideRepo.get_mapping_override"
_UPDATE = "repositories.mapping_override_repo.MappingOverrideRepo.update_mapping_override"
_GET_ANIME = "components.service_components.anilist_component.AnilistComponent.get_anime"
_GET_SERIES = "components.service_components.tvdb_component.TVDBComponent.get_series"
_AUDIT = "components.audit_log_component.AuditLogComponent.log_mapping_override_updated"


def _component() -> MappingAPIComponent:
    component = MappingAPIComponent.__new__(MappingAPIComponent)
    component._anilist_component = AnilistComponent.__new__(AnilistComponent)
    component._tvdb_component = TVDBComponent.__new__(TVDBComponent)
    return component


@dataclass
class Case:
    id: str
    exists: bool = True
    body_overrides: dict = field(default_factory=dict)
    expected_exception: type[Exception] | None = None


CASES = [
    Case(id="existing override is updated", body_overrides=dict(tvdb_season_number=2)),
    Case(id="missing override -> not found", exists=False, expected_exception=NotFoundException),
    Case(id="invalid range on existing override rejected",
         body_overrides=dict(granularity=0), expected_exception=ValidationException),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_update_mapping_override(case: Case, mocker):
    override = make_mapping_override() if case.exists else None
    mocker.patch(_GET, new_callable=AsyncMock, return_value=override)
    update = mocker.patch(_UPDATE, new_callable=AsyncMock)
    mocker.patch(_GET_ANIME, new_callable=AsyncMock, return_value=make_anime(100))
    mocker.patch(_GET_SERIES, new_callable=AsyncMock, return_value=make_tvdb_series())
    audit = mocker.patch(_AUDIT, new_callable=AsyncMock)
    body = make_mapping_request(**case.body_overrides)

    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            await _component().update_mapping_override(mapping_override_id=1, body=body)
        update.assert_not_called()
        return

    result = await _component().update_mapping_override(mapping_override_id=1, body=body)

    assert result.id == override.id
    update.assert_awaited_once()
    audit.assert_awaited_once()
