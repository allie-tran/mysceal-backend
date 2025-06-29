from enum import Enum


class ApiTargetType(str, Enum):
    JUDGEMENT = "JUDGEMENT"
    JUDGEMENT_WITH_VOTE = "JUDGEMENT_WITH_VOTE"
    MEDIA_ITEM = "MEDIA_ITEM"
    MEDIA_ITEM_TEMPORAL_RANGE = "MEDIA_ITEM_TEMPORAL_RANGE"
    TEXT = "TEXT"

    def __str__(self) -> str:
        return str(self.value)
