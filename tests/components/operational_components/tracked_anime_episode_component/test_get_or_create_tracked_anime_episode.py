from dataclasses import dataclass, field
from unittest.mock import MagicMock

import pytest

from components.operational_components.tracked_anime_episode_component import TrackedAnimeEpisodeComponent

_EP_REPO = "repositories.tracked_anime_repositories.tracked_anime_episode_repo.TrackedAnimeEpisodeRepo"
_TA_REPO = "repositories.tracked_anime_repositories.tracked_anime_repo.TrackedAnimeRepo"
_MAPPINGS = "app_state.anime_relations.get_anilist_episode_tvdb_mappings"
_POPULATE = ("components.operational_components.tracked_anime_episode_component"
             ".TrackedAnimeEpisodeComponent._populate_episode_tvdb_mappings_data")

# mapping spec: (series_id, season_number, episode_number, part, part_ceiling, episode_id)
_MAPPING = (100, 2, 5, 1, 2, 900)


@dataclass
class Case:
    id: str
    pass_tracked_anime: bool = True       # pass the object vs. only the id (forcing a repo fetch)
    pass_id: bool = True                   # when not passing the object, whether to pass the id at all
    episode_number: int = 5
    mappings: list = field(default_factory=lambda: [_MAPPING])
    existing_episode: bool = False        # repo already has the episode → update path
    set_auto_discard_to: object = None    # forwarded only when not None here
    expected_exception: type[Exception] | None = None
    expected_op: str = "create"           # 'create' | 'update'
    expected_fetches_tracked: bool = False
    expected_create_subset: dict = field(default_factory=dict)
    expected_auto_discard_present: bool = False


CASES = [
    Case(id="missing both tracked anime and id raises ValueError",
         pass_tracked_anime=False, pass_id=False, expected_exception=ValueError),
    Case(id="creates episode with tvdb mapping data",
         expected_op="create",
         expected_create_subset=dict(episode_number=5, tvdb_series_id=100, tvdb_season_number=2,
                                     tvdb_episode_numbers=[5], tvdb_episode_ids=[900],
                                     tvdb_episode_part=1, tvdb_episode_part_ceiling=2)),
    Case(id="updates the existing episode",
         existing_episode=True, expected_op="update"),
    Case(id="fetches tracked anime when only id is given",
         pass_tracked_anime=False, mappings=[], expected_op="create", expected_fetches_tracked=True),
    Case(id="no mappings writes null tvdb fields",
         mappings=[], expected_op="create",
         expected_create_subset=dict(tvdb_series_id=None, tvdb_season_number=None,
                                     tvdb_episode_numbers=[], tvdb_episode_ids=[])),
    Case(id="set_auto_discard is forwarded as an override",
         set_auto_discard_to=True, expected_op="create", expected_auto_discard_present=True),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_or_create_tracked_anime_episode(case: Case, make_component, make_tracked_anime,
                                                   make_mapping, mocker):
    tracked_anime = make_tracked_anime(anilist_id=8080)
    ta_get = mocker.patch(f"{_TA_REPO}.get_tracked_anime", return_value=tracked_anime)
    mappings = mocker.patch(_MAPPINGS, return_value=[make_mapping(series_id=s, season_number=sn,
                                                                  episode_number=en, part=p,
                                                                  part_ceiling=pc, episode_id=ei)
                                                     for (s, sn, en, p, pc, ei) in case.mappings])
    mocker.patch(_POPULATE)
    existing = MagicMock(id=777) if case.existing_episode else None
    mocker.patch(f"{_EP_REPO}.get_tracked_anime_episode", return_value=existing)
    created = MagicMock()
    ep_create = mocker.patch(f"{_EP_REPO}.create_tracked_anime_episode", return_value=created)
    ep_update = mocker.patch(f"{_EP_REPO}.update_tracked_anime_episode")

    call_kwargs = dict(episode_number=case.episode_number)
    if case.pass_tracked_anime:
        call_kwargs["tracked_anime"] = tracked_anime
    elif case.pass_id:
        call_kwargs["tracked_anime_id"] = tracked_anime.id
    if case.set_auto_discard_to is not None:
        call_kwargs["set_auto_discard_to"] = case.set_auto_discard_to

    component = make_component()

    if case.expected_exception is not None:
        with pytest.raises(case.expected_exception):
            await component.get_or_create_tracked_anime_episode(**call_kwargs)
        return

    result = await component.get_or_create_tracked_anime_episode(**call_kwargs)

    if case.expected_op == "create":
        assert result is created
        ep_update.assert_not_awaited()
        passed = ep_create.await_args.kwargs
        assert passed["tracked_anime_id"] == tracked_anime.id
    else:
        assert result is existing
        ep_create.assert_not_awaited()
        passed = ep_update.await_args.kwargs
        assert passed["tracked_anime_episode_id"] == existing.id

    for key, value in case.expected_create_subset.items():
        assert passed[key] == value
    assert ("auto_discard" in passed) == case.expected_auto_discard_present
    if case.expected_auto_discard_present:
        assert passed["auto_discard"] is case.set_auto_discard_to

    if case.expected_fetches_tracked:
        assert ta_get.await_args.kwargs["tracked_anime_id"] == tracked_anime.id
        # the anilist id used for the mapping lookup comes from the fetched tracked anime
        assert mappings.await_args.kwargs["anilist_id"] == 8080
