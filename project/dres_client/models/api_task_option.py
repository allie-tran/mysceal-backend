from enum import Enum


class ApiTaskOption(str, Enum):
    HIDDEN_RESULTS = "HIDDEN_RESULTS"
    MAP_TO_SEGMENT = "MAP_TO_SEGMENT"
    PROLONG_ON_SUBMISSION = "PROLONG_ON_SUBMISSION"

    def __str__(self) -> str:
        return str(self.value)
