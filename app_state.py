from dto.anilist import AnilistAnimeMinimal
from dto.global_status import GlobalStatus
from utils.anime_relations import AnimeRelations
from workers.downstream_healthcheck_workers import DownstreamHealthcheckWorkers
from workers.worker_manager import WorkerManagerService

# caches
ANILIST_TITLE_SEARCH_MINIMAL_RESULT: dict[str, AnilistAnimeMinimal] = {}  # title: details
ANILIST_TITLE_SEARCH_NOT_FOUND = set()
CACHED_RESPONSES = {}

# singletons
anime_relations = AnimeRelations()
downstream_healthcheck_workers = DownstreamHealthcheckWorkers()
worker_manager = WorkerManagerService()
global_status = GlobalStatus()

# password reset details
PASSWORD_RESET_CODE_DETAILS = {
    "file_path": "{data_dir}/reset_password_code.txt",
    "code": None,
}
