from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define

if TYPE_CHECKING:
    from ..models.api_temporal_point import ApiTemporalPoint


T = TypeVar("T", bound="ApiTemporalRange")


@_attrs_define
class ApiTemporalRange:
    """
    Attributes:
        start (ApiTemporalPoint):
        end (ApiTemporalPoint):
    """

    start: "ApiTemporalPoint"
    end: "ApiTemporalPoint"

    def to_dict(self) -> dict[str, Any]:
        start = self.start.to_dict()

        end = self.end.to_dict()

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "start": start,
                "end": end,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.api_temporal_point import ApiTemporalPoint

        d = dict(src_dict)
        start = ApiTemporalPoint.from_dict(d.pop("start"))

        end = ApiTemporalPoint.from_dict(d.pop("end"))

        api_temporal_range = cls(
            start=start,
            end=end,
        )

        return api_temporal_range
