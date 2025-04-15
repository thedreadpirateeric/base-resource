"""General utilities."""
from typing import Any, Tuple, List, Dict

from marshmallow import ValidationError


def chunkify_list(largeList: Any, chunkSize: int = 250) -> list:
    """Split list into smaller chunks.

    Args:
        largeList

    Kwargs:
        chunkSize: Specify how many items should be in each list. Defaults to
            250 items.

    Returns:
        list

    """
    chunkList = [largeList[x:x + chunkSize] for x
                 in range(0, len(largeList), chunkSize)]
    return chunkList


def string_to_float_or_int(value: str) -> str | float:
    """Convert string to either a float or integer."""
    strValue = int(value)
    fltValue = float(str(value))
    return strValue if strValue.is_integer() else fltValue


def marshall_load(schema: type,
                  data: List[Any] | Dict[str, Any],
                  many: bool = False) -> Tuple[Any, List[Any]]:
    """Return Loaded data."""
    errors = []
    try:
        validData = schema().load(data, many=many)
    except ValidationError as err:
        errors = err.messages
        validData = err.valid_data
    return (validData, errors)


def marshall_dump(schema: type,
                  data: List[Any] | Dict[str, Any],
                  many: bool = False) -> Tuple[Any, List[Any]]:
    """Return Dumped data."""
    errors = []
    try:
        validData = schema().dump(data, many=many)
    except ValidationError as err:
        errors = err.messages
        validData = err.valid_data
    return (validData, errors)
