from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union

from attrs import define as _attrs_define

from ..models.api_target_type import ApiTargetType
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.api_media_item import ApiMediaItem
    from ..models.api_temporal_range import ApiTemporalRange


T = TypeVar("T", bound="ApiTarget")


@_attrs_define
class ApiTarget:
    """
    Attributes:
        type_ (ApiTargetType):
        target (Union[Unset, str]):
        range_ (Union[Unset, ApiTemporalRange]):
        item (Union[Unset, ApiMediaItem]):
    """

    type_: ApiTargetType
    target: Union[Unset, str] = UNSET
    range_: Union[Unset, "ApiTemporalRange"] = UNSET
    item: Union[Unset, "ApiMediaItem"] = UNSET

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        target = self.target

        range_: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.range_, Unset):
            range_ = self.range_.to_dict()

        item: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.item, Unset):
            item = self.item.to_dict()

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "type": type_,
            }
        )
        if target is not UNSET:
            field_dict["target"] = target
        if range_ is not UNSET:
            field_dict["range"] = range_
        if item is not UNSET:
            field_dict["item"] = item

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.api_media_item import ApiMediaItem
        from ..models.api_temporal_range import ApiTemporalRange

        d = dict(src_dict)
        type_ = ApiTargetType(d.pop("type"))

        target = d.pop("target", UNSET)

        _range_ = d.pop("range", UNSET)
        range_: Union[Unset, ApiTemporalRange]
        if isinstance(_range_, Unset):
            range_ = UNSET
        else:
            range_ = ApiTemporalRange.from_dict(_range_)

        _item = d.pop("item", UNSET)
        item: Union[Unset, ApiMediaItem]
        if isinstance(_item, Unset):
            item = UNSET
        else:
            item = ApiMediaItem.from_dict(_item)

        api_target = cls(
            type_=type_,
            target=target,
            range_=range_,
            item=item,
        )

        return api_target
