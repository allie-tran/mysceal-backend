from enum import Enum


class ApiTeamAggregatorType(str, Enum):
    LAST = "LAST"
    MAX = "MAX"
    MEAN = "MEAN"
    MIN = "MIN"

    def __str__(self) -> str:
        return str(self.value)
