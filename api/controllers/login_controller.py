from api.routes import api_v1_router
from components.api_components.login_api_component import LoginAPIComponent
from api.schemas import error_responses, DataEnvelope
from api.schemas.login_schemas import LoginRequest, LoginResponse, CredentialsStatusResponse, CredentialsSetupRequest, \
    ResetPasswordRequest


@api_v1_router.post("/login", response_model=LoginResponse,
                    responses=error_responses(401))
async def authenticate(body: LoginRequest):
    return await LoginAPIComponent().authenticate(body=body)


@api_v1_router.get("/credentials-status", response_model=DataEnvelope[CredentialsStatusResponse],
                   responses=error_responses(401, 422))
async def get_credentials_status():
    return DataEnvelope(data=await LoginAPIComponent().get_credentials_status())


@api_v1_router.post("/credentials-setup", status_code=204,
                    responses=error_responses(401, 422))
async def setup_credentials(body: CredentialsSetupRequest):
    await LoginAPIComponent().setup_credentials(body=body)


@api_v1_router.post("/request-password-reset", status_code=204,
                    responses=error_responses(422))
async def request_password_reset():
    await LoginAPIComponent().request_password_reset()


@api_v1_router.post("/reset-password", status_code=204,
                    responses=error_responses(401, 422))
async def reset_password(body: ResetPasswordRequest):
    await LoginAPIComponent().reset_password(body=body)
