from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define

if TYPE_CHECKING:
    from ..models.query_event import QueryEvent
    from ..models.ranked_answer import RankedAnswer


T = TypeVar("T", bound="QueryResultLog")


@_attrs_define
class QueryResultLog:
    """
    Attributes:
        timestamp (int):
        sort_type (str):
        result_set_availability (str):
        results (list['RankedAnswer']):
        events (list['QueryEvent']):
    """

    timestamp: int
    sort_type: str
    result_set_availability: str
    results: list["RankedAnswer"]
    events: list["QueryEvent"]

    def to_dict(self) -> dict[str, Any]:
        timestamp = self.timestamp

        sort_type = self.sort_type

        result_set_availability = self.result_set_availability

        results = []
        for results_item_data in self.results:
            results_item = results_item_data.to_dict()
            results.append(results_item)

        events = []
        for events_item_data in self.events:
            events_item = events_item_data.to_dict()
            events.append(events_item)

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "timestamp": timestamp,
                "sortType": sort_type,
                "resultSetAvailability": result_set_availability,
                "results": results,
                "events": events,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.query_event import QueryEvent
        from ..models.ranked_answer import RankedAnswer

        d = dict(src_dict)
        timestamp = d.pop("timestamp")

        sort_type = d.pop("sortType")

        result_set_availability = d.pop("resultSetAvailability")

        results = []
        _results = d.pop("results")
        for results_item_data in _results:
            results_item = RankedAnswer.from_dict(results_item_data)

            results.append(results_item)

        events = []
        _events = d.pop("events")
        for events_item_data in _events:
            events_item = QueryEvent.from_dict(events_item_data)

            events.append(events_item)

        query_result_log = cls(
            timestamp=timestamp,
            sort_type=sort_type,
            result_set_availability=result_set_availability,
            results=results,
            events=events,
        )

        return query_result_log
