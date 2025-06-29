from enum import Enum


class ApiScoreOption(str, Enum):
    AVS = "AVS"
    KIS = "KIS"
    LEGACY_AVS = "LEGACY_AVS"

    def __str__(self) -> str:
        return str(self.value)
