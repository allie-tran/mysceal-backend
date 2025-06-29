from collections.abc import Mapping
from typing import Any, TypeVar, Union

from attrs import define as _attrs_define

from ..types import UNSET, Unset

T = TypeVar("T", bound="ApiMediaCollection")


@_attrs_define
class ApiMediaCollection:
    """
    Attributes:
        name (str):
        item_count (int):
        id (Union[Unset, str]):
        description (Union[Unset, str]):
        base_path (Union[Unset, str]):
    """

    name: str
    item_count: int
    id: Union[Unset, str] = UNSET
    description: Union[Unset, str] = UNSET
    base_path: Union[Unset, str] = UNSET

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        item_count = self.item_count

        id = self.id

        description = self.description

        base_path = self.base_path

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "name": name,
                "itemCount": item_count,
            }
        )
        if id is not UNSET:
            field_dict["id"] = id
        if description is not UNSET:
            field_dict["description"] = description
        if base_path is not UNSET:
            field_dict["basePath"] = base_path

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        name = d.pop("name")

        item_count = d.pop("itemCount")

        id = d.pop("id", UNSET)

        description = d.pop("description", UNSET)

        base_path = d.pop("basePath", UNSET)

        api_media_collection = cls(
            name=name,
            item_count=item_count,
            id=id,
            description=description,
            base_path=base_path,
        )

        return api_media_collection
