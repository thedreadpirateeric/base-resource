"""General utilities."""
from typing import Any


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
