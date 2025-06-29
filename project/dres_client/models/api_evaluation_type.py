from enum import Enum


class ApiEvaluationType(str, Enum):
    ASYNCHRONOUS = "ASYNCHRONOUS"
    NON_INTERACTIVE = "NON_INTERACTIVE"
    SYNCHRONOUS = "SYNCHRONOUS"

    def __str__(self) -> str:
        return str(self.value)
