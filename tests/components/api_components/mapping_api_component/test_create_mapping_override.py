from dataclasses import dataclass, field
from unittest.mock import AsyncMock

import pytest

from common.exceptions import ExternalServiceException, FailedDependencyException, ValidationException
from components.api_components.mapping_api_component import MappingAPIComponent
from components.service_components.anilist_component import AnilistComponent
from components.service_components.tvdb_component import TVDBComponent
from dto.anilist import AnilistAnime
from tests.support.builders import make_anime, make_mapping_override, make_mapping_request, make_tvdb_series

_GET_ANIME = "components.service_components.anilist_component.AnilistComponent.get_anime"
_GET_SERIES = "components.service_components.tvdb_component.TVDBComponent.get_series"
_CREATE = "repositories.mapping_override_repo.MappingOverrideRepo.create_mapping_override"
_AUDIT = "components.audit_log_component.AuditLogComponent.log_mapping_override_added_or_removed"


def _component() -> MappingAPIComponent:
    component = MappingAPIComponent.__new__(MappingAPIComponent)
    component._anilist_component = AnilistComponent.__new__(AnilistComponent)
    component._tvdb_component = TVDBComponent.__new__(TVDBComponent)
    return component


@dataclass
class Case:
    id: str
    body_overrides: dict = field(default_factory=dict)
    anime: AnilistAnime | None = field(default_factory=lambda: make_anime(100))
    series_exception: Exception | None = None
    expected_exception: type[Exception] | None = None


CASES = [
    Case(id="valid override is created"),
    Case(id="invalid range rejected before any lookup",
         body_overrides=dict(granularity=0), expected_exception=ValidationException),
    Case(id="unknown anilist id rejected", anime=None, expected_exception=ValidationException),
    Case(id="tvdb 404 surfaces as validation error",
         series_exception=ExternalServiceException("missing", status_code=404),
         expected_exception=ValidationException),
    Case(id="tvdb server error surfaces as failed dependency",
         series_exception=ExternalServiceException("boom", status_code=500),
         expected_exception=FailedDependencyException),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_create_mapping_override(case: Case, mocker):
    mocker.patch(_GET_ANIME, new_callable=AsyncMock, return_value=case.anime)
    mocker.patch(_GET_SERIES, new_callable=AsyncMock,
                 return_value=make_tvdb_series(), side_effect=case.series_exception)
    create = mocker.patch(_CREATE, new_callable=AsyncMock,
                          return_value=make_mapping_override(**case.body_overrides))
    audit = mocker.patch(_AUDIT, new_callable=AsyncMock)
    body = make_mapping_request(**case.body_overrides)

    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            await _component().create_mapping_override(body)
        create.assert_not_called()
        audit.assert_not_called()
        return

    result = await _component().create_mapping_override(body)

    assert result.id == 1
    create.assert_awaited_once()
    audit.assert_awaited_once()
