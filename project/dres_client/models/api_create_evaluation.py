from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define

T = TypeVar("T", bound="ApiCreateEvaluation")


@_attrs_define
class ApiCreateEvaluation:
    """
    Attributes:
        name (str):
        description (str):
    """

    name: str
    description: str

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        description = self.description

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "name": name,
                "description": description,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        name = d.pop("name")

        description = d.pop("description")

        api_create_evaluation = cls(
            name=name,
            description=description,
        )

        return api_create_evaluation
