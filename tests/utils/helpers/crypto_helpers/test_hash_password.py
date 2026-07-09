from dataclasses import dataclass

import pytest

from utils.helpers.crypto_helpers import hash_password, verify_password


@dataclass
class Case:
    id: str
    plaintext: str


CASES = [
    Case(id="produces a verifiable salted bcrypt hash", plaintext="s3cr3t"),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_hash_password(case: Case):
    hashed = hash_password(case.plaintext)

    assert hashed != case.plaintext
    assert hashed.startswith("$2b$")                # bcrypt identifier
    assert verify_password(hashed, case.plaintext)  # round-trips
    assert hash_password(case.plaintext) != hashed  # salted: a fresh hash of the same input differs
