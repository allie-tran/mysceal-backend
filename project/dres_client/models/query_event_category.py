from enum import Enum


class QueryEventCategory(str, Enum):
    BROWSING = "BROWSING"
    COOPERATION = "COOPERATION"
    FILTER = "FILTER"
    IMAGE = "IMAGE"
    OTHER = "OTHER"
    SKETCH = "SKETCH"
    TEXT = "TEXT"

    def __str__(self) -> str:
        return str(self.value)
