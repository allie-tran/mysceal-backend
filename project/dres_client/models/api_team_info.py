from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define

T = TypeVar("T", bound="ApiTeamInfo")


@_attrs_define
class ApiTeamInfo:
    """
    Attributes:
        id (str):
        name (str):
        color (str):
    """

    id: str
    name: str
    color: str

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        name = self.name

        color = self.color

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "id": id,
                "name": name,
                "color": color,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id")

        name = d.pop("name")

        color = d.pop("color")

        api_team_info = cls(
            id=id,
            name=name,
            color=color,
        )

        return api_team_info
