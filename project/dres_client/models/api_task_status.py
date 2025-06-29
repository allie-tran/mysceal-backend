from enum import Enum


class ApiTaskStatus(str, Enum):
    CREATED = "CREATED"
    ENDED = "ENDED"
    IGNORED = "IGNORED"
    NO_TASK = "NO_TASK"
    PREPARING = "PREPARING"
    RUNNING = "RUNNING"

    def __str__(self) -> str:
        return str(self.value)
