from enum import Enum


class ApiEvaluationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    CREATED = "CREATED"
    TERMINATED = "TERMINATED"

    def __str__(self) -> str:
        return str(self.value)
