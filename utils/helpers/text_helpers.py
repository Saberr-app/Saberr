import re
from typing import Iterable


def get_size_in_bytes(size_str: str) -> int:
    size_str = size_str.strip()
    size_units = {
        "Bytes": 1,
        "KiB": 1024,
        "MiB": 1024 ** 2,
        "GiB": 1024 ** 3,
        "TiB": 1024 ** 4,
        "B": 1,
        "KB": 1024,
        "MB": 1024 ** 2,
        "GB": 1024 ** 3,
        "TB": 1024 ** 4,
    }

    try:
        # Longest suffix first so multi-char units (e.g. "KB") are matched before the 1-char "B".
        for unit in sorted(size_units, key=len, reverse=True):
            if size_str.lower().endswith(unit.lower()):
                number_part = size_str[:-len(unit.lower())].strip()
                try:
                    size_value = float(number_part)
                    return int(size_value * size_units[unit])
                except ValueError:
                    raise ValueError(f"Invalid size value: {number_part}")

        raise ValueError(f"Unknown size unit in: {size_str}")
    except:
        return -1


def get_human_readable_size(size: int, precision: int = 2) -> str:
    if size < 1024:
        return f"{size} B"
    elif size < 1024 ** 2:
        return f"{size / 1024:.{precision}f} KB"
    elif size < 1024 ** 3:
        return f"{size / (1024 ** 2):.{precision}f} MB"
    elif size < 1024 ** 4:
        return f"{size / (1024 ** 3):.{precision}f} GB"
    else:
        return f"{size / (1024 ** 4):.{precision}f} TB"


def get_human_readable_time(seconds: int, minimal: bool = True) -> str:
    intervals = (
        ('year', 'y', 31536000),    # 365 days
        ('month', 'mo', 2592000),   # 30 days
        ('week', 'w', 604800),      # 7 days
        ('day', 'd', 86400),        # 24 hours
        ('hour', 'h', 3600),        # 60 minutes
        ('minute', 'm', 60),
        ('second', 's', 1),
    )

    result = []
    for name, abbrev, count in intervals:
        value = seconds // count
        if value:
            seconds -= value * count
            if minimal:
                result.append(f"{value}{abbrev}")
            else:
                result.append(f"{value} {name}{'s' if value > 1 else ''}")

    return (' ' if minimal else ', ').join(result) if result else 'Unresolved'


def clean_text_with_html_tags(html_text: str, extra_patterns: str | None = None) -> str:
    if extra_patterns:
        html_text = re.sub(extra_patterns, '', html_text)
    return re.sub(re.compile('<.*?>'), '', html_text).strip()


def shorten_text(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def is_valid_url(text: str) -> bool:
    pattern = (
        r"^(?:https?://)"                                                      # required scheme
        r"(?:"
        r"(?:\d{1,3}\.){3}\d{1,3}"                                              # IPv4
        r"|"
        r"(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\.)*"                      # optional sub/domain labels
        r"[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?"                             # host label (e.g. localhost)
        r")"
        r"(?::\d{1,5})?"                                                        # optional port
        r"(?:[/?#]\S*)?$"                                                       # optional path/query/fragment
    )
    return bool(re.match(pattern, text))


def validate_format_tokens(text: str, allowed_tokens: Iterable[str]):
    try:
        text.format(
            **{
                token: "" for token in allowed_tokens
            }
        )
    except KeyError as e:
        raise ValueError(f"Invalid format token: {e.args[0]}") from e


def clean_path_name(path_name: str) -> str:
    path_name = path_name.replace(":", "꞉")
    path_name = path_name.replace("/", "∕")
    path_name = path_name.replace("\\", "⑊")
    path_name = path_name.replace("?", "︖")
    path_name = path_name.replace("*", "⁎")
    quotation_marks = ["“", "”"]
    quotation_idx = 0
    while "\"" in path_name:
        path_name = path_name.replace("\"", quotation_marks[quotation_idx], 1)
        quotation_idx = 1 - quotation_idx
    path_name = path_name.replace("<", "‹")
    path_name = path_name.replace(">", "›")
    path_name = path_name.replace("|", "⏐")
    path_name = re.sub(r"\s+", " ", path_name)
    path_name = re.sub(r"[\x00-\x1f]", "", path_name)
    path_name = path_name.strip()
    path_name = path_name.rstrip(" .")
    return path_name
