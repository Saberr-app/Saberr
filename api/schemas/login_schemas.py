from pydantic import BaseModel

from api.schemas import NonEmptyString
from constants import AppContext


class LoginRequest(BaseModel):
    username: NonEmptyString
    password: NonEmptyString
    stay_logged_in: bool = False


class LoginResponse(BaseModel):
    token: str
    expires_at: int


class CredentialsStatusResponse(BaseModel):
    is_set: bool
    context: AppContext


class CredentialsSetupRequest(BaseModel):
    username: NonEmptyString
    password: NonEmptyString


class ResetPasswordRequest(BaseModel):
    reset_code: NonEmptyString | None
    old_password: NonEmptyString | None
    new_password: NonEmptyString
