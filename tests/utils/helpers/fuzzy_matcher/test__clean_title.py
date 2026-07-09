from dataclasses import dataclass

import pytest

from utils.helpers.fuzzy_matcher import _clean_title


@dataclass
class Case:
    id: str
    title: str
    expected_result: str | None


CASES = [
    Case(id="strips trailing source tag", title="Show Name BD ", expected_result="Show Name"),
    Case(id="strips leading resolution tag", title="[1080p] Show Name", expected_result="Show Name"),
    Case(id="collapses to none when only separators remain", title="  -  ", expected_result=None),
    Case(id="trims separator characters", title=" Show Name : ", expected_result="Show Name"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test__clean_title(case: Case):
    assert _clean_title(case.title) == case.expected_result
