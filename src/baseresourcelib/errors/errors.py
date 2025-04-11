"""Custom Errors."""


class BaseResourceException(Exception):
    """
    Base exception.

    Base exception for all the exception raise from base-resource.
    """


class DatabaseConnectionError(BaseResourceException):
    """Databse connection error.

    When there is connection error for the database.
    """


class ByteScaleError(BaseResourceException):
    """Byte Scaling (unit conversion) Exception."""


class TimeoutValueError(BaseResourceException):
    """API Request Timeout Value Exception."""


class ClientError4xx(BaseResourceException):
    """API Response Exceptions."""


class InvalidRequest400(BaseResourceException):
    """API Response Exceptions."""


class NothingFound404(BaseResourceException):
    """API Response Exceptions."""


class DuplicateRecord409(BaseResourceException):
    """API Response Exceptions."""


class QOperationFailed502(BaseResourceException):
    """API Response Exceptions."""


class ServerError5xx(BaseResourceException):
    """API Response Exceptions."""


class ThrottleLimitError(BaseResourceException):
    """API Response Exceptions."""


class InvalidTokenError(BaseResourceException):
    """Invalid token passed."""


class TokenExpiredError(BaseResourceException):
    """API Response Exceptions."""


class UnknownError(BaseResourceException):
    """API Response Exceptions."""


class UpstreamDependencyGone(BaseResourceException):
    """API Response Exceptions."""


class ApiRequestError(BaseResourceException):
    """Raises for any Unknown API error."""


class ClientInputError(BaseResourceException):
    """CRUD wrapper raises these."""


class HandlerMethodNotImplemented(BaseResourceException):
    """CRUD wrapper raises these."""


class HandlerCreationError(BaseResourceException):
    """CRUD wrapper raises these."""


class ConnectorMethodNotImplemented(BaseResourceException):
    """Connector raises these."""


class TaskException(BaseResourceException):
    """Top Level Exception for Tasks."""


class TaskRetry(TaskException):
    """Used if task can auto retry."""


class TaskAborted(TaskException):
    """Top Level Exception for the Aborted Status.

    Results in status = aborted and success = false
    """


class TaskIncompletedWarning(TaskException):
    """Top Level Exception for the Incomplete Status.

    Results in status = incomplete and success = true
    """


class TaskIncompletedError(TaskException):
    """Top Level Exception for the Incomplete Status.

    Results in status = incomplete and success = false
    """


class TaskFailed(TaskException):
    """Top Level Exception for the Failed Status.

    Results in status = failed and success = false
    """


class TaskTerminated(TaskException):
    """Top Level Exception for the Terminated Status.

    Results in status = terminated and success = false
    """


class TaskCrashed(TaskException):
    """Top Level Exception for the Crashed Status.

    Results in status = crashed and success = false
    """


class SnapshotError(BaseResourceException):
    """Error with the snapshots."""


class NoTimeBetweenStats(BaseResourceException):
    """No time exists between stapshot data."""
