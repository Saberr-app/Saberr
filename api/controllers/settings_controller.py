from api.routes import api_v1_router
from components.api_components.settings_api_component import SettingsAPIComponent
from api.schemas import DataEnvelope, error_responses
from api.schemas.settings_schemas import (
    SettingsResponse,
    GeneralSettings,
    ProfileSettings,
    QBitServiceSettings,
    RSSSettings,
    ProcessingSettings,
    DiscordSettings,
    AnilistLoginRequest,
    DiscordWebhookTest, AnilistUserData, QBitBaseServiceSettings
)


@api_v1_router.get("/settings", response_model=DataEnvelope[SettingsResponse])
async def get_settings():
    return DataEnvelope(data=await SettingsAPIComponent().get_settings())


@api_v1_router.put("/settings/general",
                   response_model=DataEnvelope[GeneralSettings],
                   responses=error_responses(422))
async def update_general_settings(body: GeneralSettings):
    return DataEnvelope(data=await SettingsAPIComponent().update_general_settings(body))


@api_v1_router.put("/settings/profile",
                   response_model=DataEnvelope[ProfileSettings],
                   responses=error_responses(422))
async def update_profile_settings(body: ProfileSettings):
    return DataEnvelope(data=await SettingsAPIComponent().update_profile_settings(body))


@api_v1_router.put("/settings/qbit/service",
                   response_model=DataEnvelope[SettingsResponse.QBitServiceSettingsState],
                   responses=error_responses(422))
async def update_qbit_service_settings(body: QBitServiceSettings):
    return DataEnvelope(data=await SettingsAPIComponent().update_qbit_service_settings(body))


@api_v1_router.put("/settings/rss",
                   response_model=DataEnvelope[RSSSettings],
                   responses=error_responses(422))
async def update_rss_settings(body: RSSSettings):
    return DataEnvelope(data=await SettingsAPIComponent().update_rss_settings(body))


@api_v1_router.put("/settings/processing",
                   response_model=DataEnvelope[ProcessingSettings],
                   responses=error_responses(422))
async def update_processing_settings(body: ProcessingSettings):
    return DataEnvelope(data=await SettingsAPIComponent().update_processing_settings(body))


@api_v1_router.put("/settings/discord",
                   response_model=DataEnvelope[DiscordSettings],
                   responses=error_responses(422))
async def update_discord_settings(body: DiscordSettings):
    return DataEnvelope(data=await SettingsAPIComponent().update_discord_settings(body))


@api_v1_router.post("/settings/anilist/test",
                    response_model=DataEnvelope[AnilistUserData],
                    responses=error_responses(502))
async def test_anilist_authentication(body: AnilistLoginRequest):
    return DataEnvelope(data=await SettingsAPIComponent().check_anilist_authentication(body))


@api_v1_router.post("/settings/qbit/test",
                    status_code=204,
                    responses=error_responses(502))
async def test_qbit_connection(body: QBitBaseServiceSettings):
    return DataEnvelope(data=await SettingsAPIComponent().check_qbit_connection(body))


@api_v1_router.post("/settings/discord/test",
                    status_code=204,
                    responses=error_responses(502))
async def test_discord_webhook_connection(body: DiscordWebhookTest):
    return DataEnvelope(data=await SettingsAPIComponent().test_discord_webhook_connection(body))


@api_v1_router.post("/settings/anilist/authenticate",
                    response_model=DataEnvelope[AnilistUserData],
                    responses=error_responses(422, 502))
async def authenticate_anilist(body: AnilistLoginRequest):
    return DataEnvelope(data=await SettingsAPIComponent().authenticate_anilist(body))


@api_v1_router.post("/settings/anilist/logout",
                    status_code=204)
async def logout_from_anilist():
    await SettingsAPIComponent().logout_from_anilist()
