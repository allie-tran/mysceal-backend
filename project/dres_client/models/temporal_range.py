from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define

if TYPE_CHECKING:
    from ..models.temporal_point import TemporalPoint


T = TypeVar("T", bound="TemporalRange")


@_attrs_define
class TemporalRange:
    """
    Attributes:
        start (TemporalPoint):
        end (TemporalPoint):
        center (int):
    """

    start: "TemporalPoint"
    end: "TemporalPoint"
    center: int

    def to_dict(self) -> dict[str, Any]:
        start = self.start.to_dict()

        end = self.end.to_dict()

        center = self.center

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "start": start,
                "end": end,
                "center": center,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.temporal_point import TemporalPoint

        d = dict(src_dict)
        start = TemporalPoint.from_dict(d.pop("start"))

        end = TemporalPoint.from_dict(d.pop("end"))

        center = d.pop("center")

        temporal_range = cls(
            start=start,
            end=end,
            center=center,
        )

        return temporal_range
