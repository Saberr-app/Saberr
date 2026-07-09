from dataclasses import dataclass, field

import pytest

from config import config
from tests.support.builders import make_entry
from tests.support.mocks import patch_async_returns

_EXTRAS = "components.service_components.anilist_component.AnilistComponent.get_anime_extras"
_LIST_ENTRY = ("components.service_components.anilist_list_component"
               ".AnilistListComponent.get_user_anime_list_entry")


def _payload():
    return {
        "characters": {"edges": [
            {"node": {"siteUrl": "https://c/1", "image": {"large": "c1.png"}, "name": {"full": "Hero"}},
             "role": "MAIN",
             "voiceActorRoles": [{"voiceActor": {"siteUrl": "https://va/1", "image": {"large": "va1.png"},
                                                 "name": {"full": "Seiyuu"}}}]},
            {"node": {"siteUrl": "https://c/2", "image": {"large": "c2.png"}, "name": {"full": "Sidekick"}},
             "role": "SUPPORTING", "voiceActorRoles": []},  # no voice actor → None
        ]},
        "relations": {"edges": [
            {"node": {"id": 100, "coverImage": {"large": "r.png"},
                      "title": {"english": "Seq EN", "romaji": "Seq RO", "native": "Seq NA"}, "format": "TV"},
             "relationType": "SEQUEL"},
            {"node": {"id": 101, "coverImage": {"large": "m.png"},
                      "title": {"english": "Src EN", "romaji": "Src RO", "native": "Src NA"}, "format": "MANGA"},
             "relationType": "ADAPTATION"},  # not an anime format
        ]},
        "staff": {"edges": [
            {"node": {"siteUrl": "https://s/1", "image": {"large": "s1.png"}, "name": {"full": "Director"}},
             "role": "Director"},
        ]},
    }


@dataclass
class Case:
    id: str
    extras: dict = field(default_factory=_payload)
    authenticated: bool = False
    expected_character_names: list | None = None
    expected_voice_actor_names: list | None = None       # per character, None where absent
    expected_relation_ids: list | None = None
    expected_relation_formats: list | None = None         # AnilistFormat values
    expected_relation_list_statuses: list | None = None   # AnilistAnimeUserStatus values or None
    expected_staff_names: list | None = None


CASES = [
    Case(id="maps characters, relations and staff",
         expected_character_names=["Hero", "Sidekick"], expected_voice_actor_names=["Seiyuu", None],
         expected_relation_ids=[100, 101], expected_relation_formats=["TV", "MANGA"],
         expected_relation_list_statuses=[None, None], expected_staff_names=["Director"]),
    Case(id="relation list status set only for anime formats when authenticated",
         authenticated=True, expected_relation_list_statuses=["CURRENT", None]),
    Case(id="empty extras yield empty lists",
         extras={}, expected_character_names=[], expected_relation_ids=[], expected_staff_names=[]),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_get_anime_extras(case: Case, make_component, mocker):
    targets = {_EXTRAS: case.extras}
    if case.authenticated:
        config.user_settings.anilist_user_token = "token"
        targets[_LIST_ENTRY] = make_entry(1, status="CURRENT")
    patch_async_returns(mocker, targets)

    result = await make_component().get_anime_extras(anilist_id=1, force_freshness=False)

    if case.expected_character_names is not None:
        assert [c.name for c in result.characters] == case.expected_character_names
    if case.expected_voice_actor_names is not None:
        assert [c.voice_actor.name if c.voice_actor else None
                for c in result.characters] == case.expected_voice_actor_names
    if case.expected_relation_ids is not None:
        assert [r.id for r in result.relations] == case.expected_relation_ids
    if case.expected_relation_formats is not None:
        assert [r.format.value for r in result.relations] == case.expected_relation_formats
    if case.expected_relation_list_statuses is not None:
        assert [r.list_status.value if r.list_status else None
                for r in result.relations] == case.expected_relation_list_statuses
    if case.expected_staff_names is not None:
        assert [s.name for s in result.staff] == case.expected_staff_names
