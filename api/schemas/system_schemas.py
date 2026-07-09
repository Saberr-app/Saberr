from datetime import datetime

from pydantic import BaseModel

from api.schemas import NonEmptyString


class ValidatePathRequest(BaseModel):
    path: str
    validate_writable: bool = True


class Task(BaseModel):
    class WorkerLastRun(BaseModel):
        run_succeeded: bool
        run_time: datetime
        run_duration: int
        run_error: str | None

    id: str
    name: str
    category: str
    frequency: int | None
    last_run: WorkerLastRun | None
    currently_running: bool
    currently_running_since: datetime | None


class TaskList(BaseModel):
    ref: int
    tasks: list[Task]


class SystemStats(BaseModel):
    class Disk(BaseModel):
        path: str
        name: str
        total: int | None
        used: int | None

    app_version: str
    update_available: bool
    up_since: datetime
    disk_stats: list[Disk]


class BackupItem(BaseModel):
    filename: NonEmptyString
    location: NonEmptyString
    app_version: NonEmptyString
    size: int
    created_at: datetime
    can_restore: bool


class BackupListResponse(BaseModel):
    backups: list[BackupItem]


class AppReleaseItem(BaseModel):
    web_link: str
    current_version: str  # current app version
    version: str  # latest release version
    name: str
    body: str | None  # markdown
    published_at: str  # iso format from gh
