from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union

from attrs import define as _attrs_define

from ..models.api_answer_type import ApiAnswerType
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.api_media_item import ApiMediaItem
    from ..models.temporal_range import TemporalRange


T = TypeVar("T", bound="ApiAnswer")


@_attrs_define
class ApiAnswer:
    """
    Attributes:
        type_ (ApiAnswerType):
        item (Union[Unset, ApiMediaItem]):
        text (Union[Unset, str]):
        start (Union[Unset, int]):
        end (Union[Unset, int]):
        temporal_range (Union[Unset, TemporalRange]):
    """

    type_: ApiAnswerType
    item: Union[Unset, "ApiMediaItem"] = UNSET
    text: Union[Unset, str] = UNSET
    start: Union[Unset, int] = UNSET
    end: Union[Unset, int] = UNSET
    temporal_range: Union[Unset, "TemporalRange"] = UNSET

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        item: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.item, Unset):
            item = self.item.to_dict()

        text = self.text

        start = self.start

        end = self.end

        temporal_range: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.temporal_range, Unset):
            temporal_range = self.temporal_range.to_dict()

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "type": type_,
            }
        )
        if item is not UNSET:
            field_dict["item"] = item
        if text is not UNSET:
            field_dict["text"] = text
        if start is not UNSET:
            field_dict["start"] = start
        if end is not UNSET:
            field_dict["end"] = end
        if temporal_range is not UNSET:
            field_dict["temporalRange"] = temporal_range

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.api_media_item import ApiMediaItem
        from ..models.temporal_range import TemporalRange

        d = dict(src_dict)
        type_ = ApiAnswerType(d.pop("type"))

        _item = d.pop("item", UNSET)
        item: Union[Unset, ApiMediaItem]
        if isinstance(_item, Unset):
            item = UNSET
        else:
            item = ApiMediaItem.from_dict(_item)

        text = d.pop("text", UNSET)

        start = d.pop("start", UNSET)

        end = d.pop("end", UNSET)

        _temporal_range = d.pop("temporalRange", UNSET)
        temporal_range: Union[Unset, TemporalRange]
        if isinstance(_temporal_range, Unset):
            temporal_range = UNSET
        else:
            temporal_range = TemporalRange.from_dict(_temporal_range)

        api_answer = cls(
            type_=type_,
            item=item,
            text=text,
            start=start,
            end=end,
            temporal_range=temporal_range,
        )

        return api_answer
