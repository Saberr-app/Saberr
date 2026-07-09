import re
from dataclasses import dataclass
from functools import total_ordering


@total_ordering
@dataclass(eq=False)
class AppVersion:
    major: int
    minor: int
    patch: int
    prerelease_tag: str | None = None
    prerelease_number: int | None = None
    build_metadata: str | None = None
    original_version_string: str | None = None

    @classmethod
    def from_string(cls, version_string: str) -> 'AppVersion':
        version_parts = re.match(r"^(\d+)\.(\d+)(?:\.(\d+))?(?:-(\w+)(?:\.(\d+))?)?(?:\+(\w+))?$", version_string)
        if not version_parts:
            raise ValueError(f"Invalid version string: {version_string}")
        return cls(
            major=int(version_parts.group(1)),
            minor=int(version_parts.group(2)),
            patch=int(version_parts.group(3) or 0),  # default to 0 for early builds backward compatibility
            prerelease_tag=version_parts.group(4),
            prerelease_number=int(version_parts.group(5) or 0) if version_parts.group(4) else None,
            build_metadata=version_parts.group(6),
            original_version_string=version_string
        )

    @classmethod
    def core_from_string(cls, version_string: str) -> 'AppVersion':
        return cls.from_string(version_string.split('-')[0])

    def as_core(self) -> 'AppVersion':
        return AppVersion(self.major, self.minor, self.patch)

    def _key(self):
        return (self.major, self.minor, self.patch,
                self.prerelease_tag is None,
                self.prerelease_tag or "",
                self.prerelease_number or 0)

    def __eq__(self, other): return isinstance(other, AppVersion) and self._key() == other._key()

    def __lt__(self, other): return self._key() < other._key()  # noqa
