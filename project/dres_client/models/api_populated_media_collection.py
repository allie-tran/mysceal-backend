from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define

if TYPE_CHECKING:
    from ..models.api_media_collection import ApiMediaCollection
    from ..models.api_media_item import ApiMediaItem


T = TypeVar("T", bound="ApiPopulatedMediaCollection")


@_attrs_define
class ApiPopulatedMediaCollection:
    """
    Attributes:
        collection (ApiMediaCollection):
        items (list['ApiMediaItem']):
    """

    collection: "ApiMediaCollection"
    items: list["ApiMediaItem"]

    def to_dict(self) -> dict[str, Any]:
        collection = self.collection.to_dict()

        items = []
        for items_item_data in self.items:
            items_item = items_item_data.to_dict()
            items.append(items_item)

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "collection": collection,
                "items": items,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.api_media_collection import ApiMediaCollection
        from ..models.api_media_item import ApiMediaItem

        d = dict(src_dict)
        collection = ApiMediaCollection.from_dict(d.pop("collection"))

        items = []
        _items = d.pop("items")
        for items_item_data in _items:
            items_item = ApiMediaItem.from_dict(items_item_data)

            items.append(items_item)

        api_populated_media_collection = cls(
            collection=collection,
            items=items,
        )

        return api_populated_media_collection
