import urllib.parse
from dataclasses import dataclass

from constants import ProxyProtocol
from dto import DBSettingDTO


@dataclass
class ProxyConfig(DBSettingDTO):
    host: str
    port: int
    username: str | None
    password: str | None
    protocol: ProxyProtocol

    @property
    def _bare_host(self) -> str:
        return self.host.removeprefix("http://").removeprefix("https://").strip("/")

    @property
    def url(self) -> str:
        return f"{self.protocol.value}://{self._bare_host}:{self.port}"

    def as_str(self) -> str:
        if not self.username:
            return self.url
        credentials = urllib.parse.quote(self.username, safe="")
        if self.password:
            credentials = f"{credentials}:{urllib.parse.quote(self.password, safe='')}"
        return f"{self.protocol.value}://{credentials}@{self._bare_host}:{self.port}"

    @classmethod
    def from_str(cls, proxy_str: str) -> "ProxyConfig":
        parsed = urllib.parse.urlparse(proxy_str)
        return cls(
            host=parsed.hostname,
            port=parsed.port,
            username=urllib.parse.unquote(parsed.username) if parsed.username else None,
            password=urllib.parse.unquote(parsed.password) if parsed.password else None,
            protocol=ProxyProtocol(parsed.scheme)
        )

    def to_db_setting(self) -> str:
        return self.as_str()

    def __eq__(self, other):
        return isinstance(other, ProxyConfig) and self.as_str() == other.as_str()

    def __str__(self):
        return self.as_str()
