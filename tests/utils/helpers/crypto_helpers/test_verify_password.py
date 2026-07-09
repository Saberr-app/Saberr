from dataclasses import dataclass

import pytest

from utils.helpers.crypto_helpers import hash_password, verify_password

_HASH = hash_password("correct-horse")


@dataclass
class Case:
    id: str
    candidate: str
    expected_result: bool


CASES = [
    Case(id="correct password verifies", candidate="correct-horse", expected_result=True),
    Case(id="wrong password rejected", candidate="wrong", expected_result=False),
    Case(id="empty password rejected", candidate="", expected_result=False),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_verify_password(case: Case):
    assert verify_password(_HASH, case.candidate) is case.expected_result
