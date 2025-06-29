from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define

T = TypeVar("T", bound="ApiScoreSeriesPoint")


@_attrs_define
class ApiScoreSeriesPoint:
    """
    Attributes:
        score (float):
        timestamp (int):
    """

    score: float
    timestamp: int

    def to_dict(self) -> dict[str, Any]:
        score = self.score

        timestamp = self.timestamp

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "score": score,
                "timestamp": timestamp,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        score = d.pop("score")

        timestamp = d.pop("timestamp")

        api_score_series_point = cls(
            score=score,
            timestamp=timestamp,
        )

        return api_score_series_point
