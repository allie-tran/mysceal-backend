from enum import Enum


class ApiTargetOption(str, Enum):
    JUDGEMENT = "JUDGEMENT"
    SINGLE_MEDIA_ITEM = "SINGLE_MEDIA_ITEM"
    SINGLE_MEDIA_SEGMENT = "SINGLE_MEDIA_SEGMENT"
    TEXT = "TEXT"
    VOTE = "VOTE"

    def __str__(self) -> str:
        return str(self.value)
