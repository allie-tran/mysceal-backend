from enum import Enum


class ApiTemporalUnit(str, Enum):
    FRAME_NUMBER = "FRAME_NUMBER"
    MILLISECONDS = "MILLISECONDS"
    SECONDS = "SECONDS"
    TIMECODE = "TIMECODE"

    def __str__(self) -> str:
        return str(self.value)
