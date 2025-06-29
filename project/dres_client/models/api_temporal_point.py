from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define

from ..models.api_temporal_unit import ApiTemporalUnit

T = TypeVar("T", bound="ApiTemporalPoint")


@_attrs_define
class ApiTemporalPoint:
    """
    Attributes:
        value (str):
        unit (ApiTemporalUnit):
    """

    value: str
    unit: ApiTemporalUnit

    def to_dict(self) -> dict[str, Any]:
        value = self.value

        unit = self.unit.value

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "value": value,
                "unit": unit,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        value = d.pop("value")

        unit = ApiTemporalUnit(d.pop("unit"))

        api_temporal_point = cls(
            value=value,
            unit=unit,
        )

        return api_temporal_point
