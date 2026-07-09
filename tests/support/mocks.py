"""Helpers for the mocker-driven test convention.

`patch_async_returns` / `patch_returns` stub a set of dotted targets with mocks that return values
taken from a Case's fields, removing the per-dependency fixture boilerplate.
"""
from unittest.mock import AsyncMock

from pytest_mock import MockerFixture


def patch_async_returns(mocker: MockerFixture, mapping: dict[str, object]) -> dict[str, AsyncMock]:
    """Patch each dotted async target with an AsyncMock returning the mapped value.

    Returns {target: mock} so the runner can assert calls when needed.
    """
    return {target: mocker.patch(target, new_callable=AsyncMock, return_value=value)
            for target, value in mapping.items()}


def patch_returns(mocker: MockerFixture, mapping: dict[str, object]) -> dict[str, object]:
    """Patch each dotted sync target with a Mock returning the mapped value."""
    return {target: mocker.patch(target, return_value=value)
            for target, value in mapping.items()}
