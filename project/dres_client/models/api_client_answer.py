from collections.abc import Mapping
from typing import Any, TypeVar, Union, cast

from attrs import define as _attrs_define

from ..types import UNSET, Unset

T = TypeVar("T", bound="ApiClientAnswer")


@_attrs_define
class ApiClientAnswer:
    """
    Attributes:
        text (Union[None, Unset, str]):
        media_item_name (Union[None, Unset, str]):
        media_item_collection_name (Union[None, Unset, str]):
        start (Union[None, Unset, int]):
        end (Union[None, Unset, int]):
    """

    text: Union[None, Unset, str] = UNSET
    media_item_name: Union[None, Unset, str] = UNSET
    media_item_collection_name: Union[None, Unset, str] = UNSET
    start: Union[None, Unset, int] = UNSET
    end: Union[None, Unset, int] = UNSET

    def to_dict(self) -> dict[str, Any]:
        text: Union[None, Unset, str]
        if isinstance(self.text, Unset):
            text = UNSET
        else:
            text = self.text

        media_item_name: Union[None, Unset, str]
        if isinstance(self.media_item_name, Unset):
            media_item_name = UNSET
        else:
            media_item_name = self.media_item_name

        media_item_collection_name: Union[None, Unset, str]
        if isinstance(self.media_item_collection_name, Unset):
            media_item_collection_name = UNSET
        else:
            media_item_collection_name = self.media_item_collection_name

        start: Union[None, Unset, int]
        if isinstance(self.start, Unset):
            start = UNSET
        else:
            start = self.start

        end: Union[None, Unset, int]
        if isinstance(self.end, Unset):
            end = UNSET
        else:
            end = self.end

        field_dict: dict[str, Any] = {}

        field_dict.update({})
        if text is not UNSET:
            field_dict["text"] = text
        if media_item_name is not UNSET:
            field_dict["mediaItemName"] = media_item_name
        if media_item_collection_name is not UNSET:
            field_dict["mediaItemCollectionName"] = media_item_collection_name
        if start is not UNSET:
            field_dict["start"] = start
        if end is not UNSET:
            field_dict["end"] = end

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)

        def _parse_text(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        text = _parse_text(d.pop("text", UNSET))

        def _parse_media_item_name(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        media_item_name = _parse_media_item_name(d.pop("mediaItemName", UNSET))

        def _parse_media_item_collection_name(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        media_item_collection_name = _parse_media_item_collection_name(d.pop("mediaItemCollectionName", UNSET))

        def _parse_start(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        start = _parse_start(d.pop("start", UNSET))

        def _parse_end(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        end = _parse_end(d.pop("end", UNSET))

        api_client_answer = cls(
            text=text,
            media_item_name=media_item_name,
            media_item_collection_name=media_item_collection_name,
            start=start,
            end=end,
        )

        return api_client_answer
