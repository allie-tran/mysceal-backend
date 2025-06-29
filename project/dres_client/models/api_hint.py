from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union

from attrs import define as _attrs_define

from ..models.api_hint_type import ApiHintType
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.api_media_item import ApiMediaItem
    from ..models.api_temporal_range import ApiTemporalRange


T = TypeVar("T", bound="ApiHint")


@_attrs_define
class ApiHint:
    """
    Attributes:
        type_ (ApiHintType):
        start (Union[Unset, int]):
        end (Union[Unset, int]):
        description (Union[Unset, str]):
        path (Union[Unset, str]):
        data_type (Union[Unset, str]):
        item (Union[Unset, ApiMediaItem]):
        range_ (Union[Unset, ApiTemporalRange]):
    """

    type_: ApiHintType
    start: Union[Unset, int] = UNSET
    end: Union[Unset, int] = UNSET
    description: Union[Unset, str] = UNSET
    path: Union[Unset, str] = UNSET
    data_type: Union[Unset, str] = UNSET
    item: Union[Unset, "ApiMediaItem"] = UNSET
    range_: Union[Unset, "ApiTemporalRange"] = UNSET

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        start = self.start

        end = self.end

        description = self.description

        path = self.path

        data_type = self.data_type

        item: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.item, Unset):
            item = self.item.to_dict()

        range_: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.range_, Unset):
            range_ = self.range_.to_dict()

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "type": type_,
            }
        )
        if start is not UNSET:
            field_dict["start"] = start
        if end is not UNSET:
            field_dict["end"] = end
        if description is not UNSET:
            field_dict["description"] = description
        if path is not UNSET:
            field_dict["path"] = path
        if data_type is not UNSET:
            field_dict["dataType"] = data_type
        if item is not UNSET:
            field_dict["item"] = item
        if range_ is not UNSET:
            field_dict["range"] = range_

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.api_media_item import ApiMediaItem
        from ..models.api_temporal_range import ApiTemporalRange

        d = dict(src_dict)
        type_ = ApiHintType(d.pop("type"))

        start = d.pop("start", UNSET)

        end = d.pop("end", UNSET)

        description = d.pop("description", UNSET)

        path = d.pop("path", UNSET)

        data_type = d.pop("dataType", UNSET)

        _item = d.pop("item", UNSET)
        item: Union[Unset, ApiMediaItem]
        if isinstance(_item, Unset):
            item = UNSET
        else:
            item = ApiMediaItem.from_dict(_item)

        _range_ = d.pop("range", UNSET)
        range_: Union[Unset, ApiTemporalRange]
        if isinstance(_range_, Unset):
            range_ = UNSET
        else:
            range_ = ApiTemporalRange.from_dict(_range_)

        api_hint = cls(
            type_=type_,
            start=start,
            end=end,
            description=description,
            path=path,
            data_type=data_type,
            item=item,
            range_=range_,
        )

        return api_hint
