from enum import Enum


class ApiAnswerType(str, Enum):
    ITEM = "ITEM"
    TEMPORAL = "TEMPORAL"
    TEXT = "TEXT"

    def __str__(self) -> str:
        return str(self.value)
