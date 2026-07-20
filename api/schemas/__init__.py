from typing import Annotated, TypeAlias

from pydantic import AfterValidator, BaseModel, Field, StringConstraints
from typing import Generic, TypeVar

from components.external_image_component import ExternalImageComponent
from config import config

T = TypeVar("T")


class DataEnvelope(BaseModel, Generic[T]):
    data: T


def non_empty_str() -> type[str]:
    return Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


NonEmptyString: TypeAlias = non_empty_str()


def int_in_range(*,
                 ge: int | None = None,
                 le: int | None = None,
                 gt: int | None = None,
                 lt: int | None = None) -> type[int]:
    return Annotated[int, Field(ge=ge, le=le, gt=gt, lt=lt)]


def digit_str(*, max_len: int = 255) -> type[str]:
    return Annotated[str, Field(pattern=r"^\d+$", max_length=max_len)]


def bounded_list(item_type: type[T], *, min_len: int | None = None, max_len: int | None = None) -> type[list]:
    # noinspection PyTypeHints
    return Annotated[list[item_type], Field(min_length=min_len, max_length=max_len)]


def data_response(data: dict) -> DataEnvelope[dict]:
    return DataEnvelope(data=data)


class ErrorResponse(BaseModel):
    detail: str
    code: str


def error_responses(*status_codes: int) -> dict:
    return {code: {"model": ErrorResponse} for code in status_codes}


def _to_cached_asset_url(value: str | None) -> str | None:
    if value is None \
            or not config.proxy_external_images \
            or value.startswith("/images"):  # avoid recursive encodings (e.g. .model_dump() calls)
        return value
    try:
        return f"/images/{ExternalImageComponent().get_encoded_external_image_url(value)}"
    except Exception:
        return value


def cached_asset() -> type[str | None]:
    return Annotated[str | None, AfterValidator(_to_cached_asset_url)]
