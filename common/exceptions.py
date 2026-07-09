
class BaseSaberrException(Exception):
    """Base exception class for Saberr."""
    DEFAULT_MESSAGE = "An error occurred."

    def __init__(self, detail=None):
        self.detail = detail or self.DEFAULT_MESSAGE
        super().__init__(self.detail)


# --- API Exceptions ---


class BaseAPIException(BaseSaberrException):
    """Base API exception class."""
    status_code = 500
    default_detail = 'An error occurred.'
    default_code = 'ERROR'

    def __init__(self, detail=None, code=None):
        super().__init__(detail)
        if detail is not None:
            self.detail = detail
        else:
            self.detail = self.default_detail

        if code is not None:
            self.code = code
        else:
            self.code = self.default_code


class BadRequestException(BaseAPIException):
    """Exception for bad requests."""
    status_code = 400
    default_detail = 'The request was invalid.'
    default_code = 'BAD_REQUEST'


class UnauthorizedException(BaseAPIException):
    """Exception for unauthorized access."""
    status_code = 401
    default_detail = 'Unauthorized access.'
    default_code = 'UNAUTHORIZED'


class NotFoundException(BaseAPIException):
    """Exception for not found resources."""
    status_code = 404
    default_detail = 'The requested resource was not found.'
    default_code = 'NOT_FOUND'


class ValidationException(BaseAPIException):
    """Exception for validation failed in requests."""
    status_code = 422
    default_detail = 'Invalid input.'
    default_code = 'VALIDATION_FAILED'


class ResourceLockedException(BaseAPIException):
    """Exception for resource locked."""
    status_code = 423
    default_detail = 'Resource is locked.'
    default_code = 'RESOURCE_LOCKED'


class FailedDependencyException(BaseAPIException):
    """External dependency failed."""
    status_code = 424
    default_detail = 'Failed dependency.'
    default_code = 'FAILED_DEPENDENCY'


class BadGatewayException(BaseAPIException):
    """Exception for errors from external services."""
    status_code = 502
    default_detail = 'External service error.'
    default_code = 'BAD_GATEWAY'


# --- App Exceptions ---


class ExternalServiceException(BaseSaberrException):
    """Exception for errors from external services."""
    def __init__(self, detail=None, status_code=None, debug_info: dict = None):
        self.detail = detail or f"An error occurred."
        self.status_code = status_code
        self.debug_info = debug_info or {}
        super().__init__(self.detail)


class AnilistNotAuthenticatedException(BaseSaberrException):
    DEFAULT_MESSAGE = "Anilist authentication required."


class AnilistUnauthorizedException(BaseSaberrException):
    DEFAULT_MESSAGE = "Unauthorized access to Anilist API. Try re-authenticating."


class AnilistNotFoundException(BaseSaberrException):
    DEFAULT_MESSAGE = "Requested Anilist resource not found."


class QbitNotConfiguredException(BaseSaberrException):
    DEFAULT_MESSAGE = "qBittorrent is not configured."


class TVDBIncompleteDataException(BaseSaberrException):
    DEFAULT_MESSAGE = "TVDB data incomplete."


class TorrentReleaseGroupMatchException(BaseSaberrException):
    DEFAULT_MESSAGE = "No matching release group found for torrent."


class TorrentTitleParseException(BaseSaberrException):
    DEFAULT_MESSAGE = "Failed to parse torrent title with the available regex."


class AnilistRelationsEpisodeCountMismatch(BaseSaberrException):
    DEFAULT_MESSAGE = "Torrent resolved to either a partial episode or multiple episodes."


class TorrentEpisodeCountMismatch(BaseSaberrException):
    DEFAULT_MESSAGE = "Torrent resolved to an uneven partitioning of episodes on AniList/TVDB."


class PreprocessingFailedException(BaseSaberrException):
    DEFAULT_MESSAGE = "Failed to prepare torrent for processing."


class InvalidSettingValueException(BaseSaberrException):
    DEFAULT_MESSAGE = "Invalid setting value."


class InvalidReleaseGroupException(BaseSaberrException):
    DEFAULT_MESSAGE = "Invalid release group."


class ObjectNotFoundException(BaseSaberrException):
    DEFAULT_MESSAGE = "Object not found."


class WorkerAlreadyRunningException(BaseSaberrException):
    DEFAULT_MESSAGE = "Worker already running."


class ExternalImageURLDecodeException(BaseSaberrException):
    DEFAULT_MESSAGE = "Failed to decode cached asset."


class InvalidBackupException(BaseSaberrException):
    DEFAULT_MESSAGE = "Invalid or unusable backup archive."
