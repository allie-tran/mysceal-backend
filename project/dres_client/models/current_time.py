from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define

T = TypeVar("T", bound="CurrentTime")


@_attrs_define
class CurrentTime:
    """
    Attributes:
        time_stamp (int):
    """

    time_stamp: int

    def to_dict(self) -> dict[str, Any]:
        time_stamp = self.time_stamp

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "timeStamp": time_stamp,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        time_stamp = d.pop("timeStamp")

        current_time = cls(
            time_stamp=time_stamp,
        )

        return current_time
