from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define

from ..models.api_verdict_status import ApiVerdictStatus

T = TypeVar("T", bound="SuccessfulSubmissionsStatus")


@_attrs_define
class SuccessfulSubmissionsStatus:
    """
    Attributes:
        status (bool):
        submission (ApiVerdictStatus):
        description (str):
    """

    status: bool
    submission: ApiVerdictStatus
    description: str

    def to_dict(self) -> dict[str, Any]:
        status = self.status

        submission = self.submission.value

        description = self.description

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "status": status,
                "submission": submission,
                "description": description,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        status = d.pop("status")

        submission = ApiVerdictStatus(d.pop("submission"))

        description = d.pop("description")

        successful_submissions_status = cls(
            status=status,
            submission=submission,
            description=description,
        )

        return successful_submissions_status
