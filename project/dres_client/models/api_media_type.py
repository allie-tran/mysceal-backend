from enum import Enum


class ApiMediaType(str, Enum):
    IMAGE = "IMAGE"
    TEXT = "TEXT"
    VIDEO = "VIDEO"

    def __str__(self) -> str:
        return str(self.value)
