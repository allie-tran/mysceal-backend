from enum import Enum


class ApiHintOption(str, Enum):
    EXTERNAL_IMAGE = "EXTERNAL_IMAGE"
    EXTERNAL_VIDEO = "EXTERNAL_VIDEO"
    IMAGE_ITEM = "IMAGE_ITEM"
    TEXT = "TEXT"
    VIDEO_ITEM_SEGMENT = "VIDEO_ITEM_SEGMENT"

    def __str__(self) -> str:
        return str(self.value)
