from dataclasses import dataclass

import pytest

from utils.helpers.path_helpers import get_disk_for_path


@dataclass
class Case:
    id: str
    nested_missing: bool  # resolve a path that does not exist (disk_usage raises)
    expects_usage: bool


CASES = [
    Case(id="real path yields mount and usage", nested_missing=False, expects_usage=True),
    # disk_usage raises for a non-existent path; the mount is still resolved by walking up
    Case(id="missing path yields a mount but no usage", nested_missing=True, expects_usage=False),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_get_disk_for_path(case: Case, tmp_path):
    path = tmp_path / "does" / "not" / "exist" if case.nested_missing else tmp_path

    mount, total, used = get_disk_for_path(str(path))

    assert isinstance(mount, str) and mount
    if case.expects_usage:
        assert isinstance(total, int) and total > 0
        assert isinstance(used, int) and used >= 0
        assert used <= total
    else:
        assert total is None
        assert used is None
