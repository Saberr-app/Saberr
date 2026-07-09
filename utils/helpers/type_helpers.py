from typing import Any


def require_str(value: Any, nullable: bool = False, min_length: int = None, max_length: int = None,
                new_lines_allowed: bool = True) -> None:
    if nullable and value is None:
        return
    if not isinstance(value, str):
        suffix = " or null" if nullable else ""
        raise TypeError(f"Value must be a string{suffix}, got {type(value).__name__}.")
    if min_length is not None and len(value) < min_length:
        raise ValueError(f"Value must be at least {min_length} characters long, got {len(value)}.")
    if max_length is not None and len(value) > max_length:
        raise ValueError(f"Value must be at most {max_length} characters long, got {len(value)}.")
    if not new_lines_allowed and "\n" in value:
        raise ValueError("New lines are not allowed in this field.")


def require_bool(value: Any, nullable: bool = False) -> None:
    if nullable and value is None:
        return
    if not isinstance(value, bool):
        suffix = " or null" if nullable else ""
        raise TypeError(f"Value must be a boolean{suffix}, got {type(value).__name__}.")


def require_int(value: Any, nullable: bool = False, minimum_value: int = None) -> None:
    if nullable and value is None:
        return
    # bool is a subclass of int, so reject it explicitly
    if isinstance(value, bool) or not isinstance(value, int):
        suffix = " or null" if nullable else ""
        raise TypeError(f"Value must be an integer{suffix}, got {type(value).__name__}.")
    if minimum_value is not None and value < minimum_value:
        raise ValueError(f"Value must be at least {minimum_value}, got {value}.")


def require_digit_str(value: Any, nullable: bool = False) -> None:
    if nullable and value is None:
        return
    if not isinstance(value, str) or not value.isdigit():
        suffix = " or null" if nullable else ""
        raise TypeError(f"Value must be a digit string{suffix}, got {type(value).__name__}.")


def require_iterable(value: Any, nullable: bool = False, size: int = None) -> None:
    if nullable and value is None:
        return
    if not isinstance(value, (list, tuple, set)):
        suffix = " or null" if nullable else ""
        raise TypeError(f"Value must be an iterable{suffix}, got {type(value).__name__}.")
    if size is not None and len(value) != size:
        raise ValueError(f"Value must have {size} items, got {len(value)}.")
