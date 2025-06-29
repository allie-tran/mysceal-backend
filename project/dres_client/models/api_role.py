from enum import Enum


class ApiRole(str, Enum):
    ADMIN = "ADMIN"
    ANYONE = "ANYONE"
    JUDGE = "JUDGE"
    PARTICIPANT = "PARTICIPANT"
    VIEWER = "VIEWER"

    def __str__(self) -> str:
        return str(self.value)
