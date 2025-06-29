from collections.abc import Mapping
from typing import Any, TypeVar, Union

from attrs import define as _attrs_define

from ..types import UNSET, Unset

T = TypeVar("T", bound="ApiTaskGroup")


@_attrs_define
class ApiTaskGroup:
    """
    Attributes:
        name (str):
        type_ (str):
        id (Union[Unset, str]):
    """

    name: str
    type_: str
    id: Union[Unset, str] = UNSET

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        type_ = self.type_

        id = self.id

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "name": name,
                "type": type_,
            }
        )
        if id is not UNSET:
            field_dict["id"] = id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        name = d.pop("name")

        type_ = d.pop("type")

        id = d.pop("id", UNSET)

        api_task_group = cls(
            name=name,
            type_=type_,
            id=id,
        )

        return api_task_group
