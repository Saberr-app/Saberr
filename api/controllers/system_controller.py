from collections.abc import AsyncIterator

from fastapi.sse import EventSourceResponse, ServerSentEvent
from starlette.requests import Request

from api.controllers import minimal_polling_sse
from api.routes import api_v1_router
from components.api_components.system_api_component import SystemAPIComponent
from api.schemas import error_responses, DataEnvelope
from api.schemas.system_schemas import ValidatePathRequest, TaskList, SystemStats, BackupListResponse, \
    BackupItem, AppReleaseItem


@api_v1_router.post("/system/validate-path",
                    status_code=204,
                    responses=error_responses(422))
async def validate_path(body: ValidatePathRequest):
    await SystemAPIComponent().validate_path(body=body)


@api_v1_router.get("/system/tasks",
                   response_model=DataEnvelope[TaskList])
async def list_tasks():
    return DataEnvelope(data=await SystemAPIComponent().get_list_of_tasks())


@api_v1_router.get("/system/tasks/stream", response_class=EventSourceResponse)
async def list_tasks_stream(request: Request, freq: int = 3) -> AsyncIterator[ServerSentEvent]:
    async for event in minimal_polling_sse(request=request,
                                           callable_=SystemAPIComponent().get_list_of_tasks,
                                           frequency=freq,
                                           nullify_func=SystemAPIComponent.nullify_unchanged):
        yield event


@api_v1_router.post("/system/tasks/{task_id}/trigger",
                    status_code=204,
                    responses=error_responses(423))
async def trigger_task(task_id: str):
    await SystemAPIComponent().trigger_task(task_id=task_id)


@api_v1_router.get("/system/stats", response_model=DataEnvelope[SystemStats])
async def system_stats():
    return DataEnvelope(data=await SystemAPIComponent().get_system_stats())


@api_v1_router.post("/system/shutdown",
                    status_code=204)
async def shutdown():
    await SystemAPIComponent().shutdown()


@api_v1_router.get("/system/backups", response_model=DataEnvelope[BackupListResponse])
async def get_backups():
    return DataEnvelope(data=await SystemAPIComponent().get_list_of_backups())


@api_v1_router.post("/system/backups", response_model=DataEnvelope[BackupItem],
                    responses=error_responses(422))
async def create_backup():
    return DataEnvelope(data=await SystemAPIComponent().create_backup())


@api_v1_router.post("/system/backups/{filename}/restore", status_code=204)
async def restore_backup(filename: str):
    return DataEnvelope(data=await SystemAPIComponent().request_backup_restore(filename=filename))


@api_v1_router.delete("/system/backups/{filename}", status_code=204)
async def delete_backup(filename: str):
    return DataEnvelope(data=await SystemAPIComponent().delete_backup(filename=filename))


@api_v1_router.get("/system/app-releases/current", response_model=DataEnvelope[AppReleaseItem])
async def get_current_app_release():
    return DataEnvelope(data=await SystemAPIComponent().get_current_app_release())


@api_v1_router.get("/system/app-releases/latest", response_model=DataEnvelope[AppReleaseItem])
async def get_latest_app_release():
    return DataEnvelope(data=await SystemAPIComponent().get_latest_app_release())
