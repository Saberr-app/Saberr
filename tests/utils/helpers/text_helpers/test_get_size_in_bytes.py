from dataclasses import dataclass

import pytest

from utils.helpers.text_helpers import get_size_in_bytes


@dataclass
class Case:
    id: str
    size_str: str
    expected_result: int


CASES = [
    # binary units
    Case(id="1 KiB", size_str="1 KiB", expected_result=1024),
    Case(id="1 MiB", size_str="1 MiB", expected_result=1024 ** 2),
    Case(id="1 GiB", size_str="1 GiB", expected_result=1024 ** 3),
    Case(id="1 TiB", size_str="1 TiB", expected_result=1024 ** 4),
    Case(id="1.5 GiB", size_str="1.5 GiB", expected_result=int(1.5 * 1024 ** 3)),
    # decimal units (regression: these used to all return -1)
    Case(id="10 KB", size_str="10 KB", expected_result=10 * 1024),
    Case(id="5 MB", size_str="5 MB", expected_result=5 * 1024 ** 2),
    Case(id="2 GB", size_str="2 GB", expected_result=2 * 1024 ** 3),
    Case(id="1 TB", size_str="1 TB", expected_result=1024 ** 4),
    # plain bytes
    Case(id="500 B", size_str="500 B", expected_result=500),
    Case(id="1024 Bytes", size_str="1024 Bytes", expected_result=1024),
    # formatting tolerance
    Case(id="surrounding whitespace", size_str="  1 KiB  ", expected_result=1024),
    Case(id="lowercase unit", size_str="1gib", expected_result=1024 ** 3),
    # invalid input -> -1
    Case(id="garbage", size_str="garbage", expected_result=-1),
    Case(id="number without unit", size_str="10", expected_result=-1),
    Case(id="empty string", size_str="", expected_result=-1),
    Case(id="non-numeric magnitude", size_str="abc KB", expected_result=-1),
    Case(id="unit only", size_str="KB", expected_result=-1),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_get_size_in_bytes(case: Case):
    assert get_size_in_bytes(case.size_str) == case.expected_result
