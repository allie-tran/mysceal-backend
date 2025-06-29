from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define

from ..models.query_event_category import QueryEventCategory

T = TypeVar("T", bound="QueryEvent")


@_attrs_define
class QueryEvent:
    """
    Attributes:
        timestamp (int):
        category (QueryEventCategory):
        type_ (str):
        value (str):
    """

    timestamp: int
    category: QueryEventCategory
    type_: str
    value: str

    def to_dict(self) -> dict[str, Any]:
        timestamp = self.timestamp

        category = self.category.value

        type_ = self.type_

        value = self.value

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "timestamp": timestamp,
                "category": category,
                "type": type_,
                "value": value,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        timestamp = d.pop("timestamp")

        category = QueryEventCategory(d.pop("category"))

        type_ = d.pop("type")

        value = d.pop("value")

        query_event = cls(
            timestamp=timestamp,
            category=category,
            type_=type_,
            value=value,
        )

        return query_event
