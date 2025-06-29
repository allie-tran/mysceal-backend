from enum import Enum


class ApiVerdictStatus(str, Enum):
    CORRECT = "CORRECT"
    INDETERMINATE = "INDETERMINATE"
    UNDECIDABLE = "UNDECIDABLE"
    WRONG = "WRONG"

    def __str__(self) -> str:
        return str(self.value)
