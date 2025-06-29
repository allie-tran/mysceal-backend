from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define

T = TypeVar("T", bound="SuccessStatus")


@_attrs_define
class SuccessStatus:
    """
    Attributes:
        status (bool):
        description (str):
    """

    status: bool
    description: str

    def to_dict(self) -> dict[str, Any]:
        status = self.status

        description = self.description

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "status": status,
                "description": description,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        status = d.pop("status")

        description = d.pop("description")

        success_status = cls(
            status=status,
            description=description,
        )

        return success_status
