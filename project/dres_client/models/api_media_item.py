from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union

from attrs import define as _attrs_define

from ..models.api_media_type import ApiMediaType
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.api_media_item_meta_data_entry import ApiMediaItemMetaDataEntry


T = TypeVar("T", bound="ApiMediaItem")


@_attrs_define
class ApiMediaItem:
    """
    Attributes:
        media_item_id (str):
        name (str):
        type_ (ApiMediaType):
        collection_id (str):
        location (str):
        metadata (list['ApiMediaItemMetaDataEntry']):
        duration_ms (Union[Unset, int]):
        fps (Union[Unset, float]):
    """

    media_item_id: str
    name: str
    type_: ApiMediaType
    collection_id: str
    location: str
    metadata: list["ApiMediaItemMetaDataEntry"]
    duration_ms: Union[Unset, int] = UNSET
    fps: Union[Unset, float] = UNSET

    def to_dict(self) -> dict[str, Any]:
        media_item_id = self.media_item_id

        name = self.name

        type_ = self.type_.value

        collection_id = self.collection_id

        location = self.location

        metadata = []
        for metadata_item_data in self.metadata:
            metadata_item = metadata_item_data.to_dict()
            metadata.append(metadata_item)

        duration_ms = self.duration_ms

        fps = self.fps

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "mediaItemId": media_item_id,
                "name": name,
                "type": type_,
                "collectionId": collection_id,
                "location": location,
                "metadata": metadata,
            }
        )
        if duration_ms is not UNSET:
            field_dict["durationMs"] = duration_ms
        if fps is not UNSET:
            field_dict["fps"] = fps

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.api_media_item_meta_data_entry import ApiMediaItemMetaDataEntry

        d = dict(src_dict)
        media_item_id = d.pop("mediaItemId")

        name = d.pop("name")

        type_ = ApiMediaType(d.pop("type"))

        collection_id = d.pop("collectionId")

        location = d.pop("location")

        metadata = []
        _metadata = d.pop("metadata")
        for metadata_item_data in _metadata:
            metadata_item = ApiMediaItemMetaDataEntry.from_dict(metadata_item_data)

            metadata.append(metadata_item)

        duration_ms = d.pop("durationMs", UNSET)

        fps = d.pop("fps", UNSET)

        api_media_item = cls(
            media_item_id=media_item_id,
            name=name,
            type_=type_,
            collection_id=collection_id,
            location=location,
            metadata=metadata,
            duration_ms=duration_ms,
            fps=fps,
        )

        return api_media_item
