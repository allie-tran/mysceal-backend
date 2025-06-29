from enum import Enum


class ApiContentType(str, Enum):
    EMPTY = "EMPTY"
    IMAGE = "IMAGE"
    TEXT = "TEXT"
    VIDEO = "VIDEO"

    def __str__(self) -> str:
        return str(self.value)
