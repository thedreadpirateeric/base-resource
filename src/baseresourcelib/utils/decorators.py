"""BsLib Decorators."""
import os
from typing import Any
from ast import literal_eval
from functools import wraps

from ..errors.errors import TimeoutValueError
from .utils import string_to_float_or_int


def validate_timeout(func):
    """Validate python requests timeout input."""
    @wraps(func)
    def execute(*args: list, _timeout: Any = None, **kwargs: dict):
        if _timeout is None:
            _timeout = str(os.environ.get("API_REQUEST_TIMEOUT", 120))

        errMsg = (
            f"Invalid timeout value -> `{_timeout}`. "
            "Timeout value must be an integer, a float, or "
            "a tuple (of length 2) containing integers, floats or "
            "a mixture of both.  Example: 4 or 2.12, or (3, 4.07)")

        _timeout = str(_timeout)

        replaceChars = ["(", ")"]
        for _char in replaceChars:
            _timeout = _timeout.replace(_char, "")

        try:
            # tuple
            _timeout = literal_eval(_timeout)
        except (SyntaxError, ValueError) as exc:
            raise TimeoutValueError(errMsg) from exc

        if isinstance(_timeout, tuple):
            if len(_timeout) != 2:
                raise TimeoutValueError(errMsg)
            _rtimeout = []
            for item in _timeout:
                try:
                    item = string_to_float_or_int(item)
                except ValueError as exc:
                    raise TimeoutValueError(errMsg) from exc
                _rtimeout.append(item)
            _timeout = tuple(_rtimeout)
        else:
            try:
                _timeout = string_to_float_or_int(str(_timeout))
            except ValueError as exc:
                raise TimeoutValueError(errMsg) from exc

        kwargs['timeout'] = _timeout
        return func(*args, **kwargs)
    return execute
