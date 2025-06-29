from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define

if TYPE_CHECKING:
    from ..models.query_event import QueryEvent


T = TypeVar("T", bound="QueryEventLog")


@_attrs_define
class QueryEventLog:
    """
    Attributes:
        timestamp (int):
        events (list['QueryEvent']):
    """

    timestamp: int
    events: list["QueryEvent"]

    def to_dict(self) -> dict[str, Any]:
        timestamp = self.timestamp

        events = []
        for events_item_data in self.events:
            events_item = events_item_data.to_dict()
            events.append(events_item)

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "timestamp": timestamp,
                "events": events,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.query_event import QueryEvent

        d = dict(src_dict)
        timestamp = d.pop("timestamp")

        events = []
        _events = d.pop("events")
        for events_item_data in _events:
            events_item = QueryEvent.from_dict(events_item_data)

            events.append(events_item)

        query_event_log = cls(
            timestamp=timestamp,
            events=events,
        )

        return query_event_log
