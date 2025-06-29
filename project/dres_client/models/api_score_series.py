from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define

if TYPE_CHECKING:
    from ..models.api_score_series_point import ApiScoreSeriesPoint


T = TypeVar("T", bound="ApiScoreSeries")


@_attrs_define
class ApiScoreSeries:
    """
    Attributes:
        team (str):
        name (str):
        points (list['ApiScoreSeriesPoint']):
    """

    team: str
    name: str
    points: list["ApiScoreSeriesPoint"]

    def to_dict(self) -> dict[str, Any]:
        team = self.team

        name = self.name

        points = []
        for points_item_data in self.points:
            points_item = points_item_data.to_dict()
            points.append(points_item)

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "team": team,
                "name": name,
                "points": points,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.api_score_series_point import ApiScoreSeriesPoint

        d = dict(src_dict)
        team = d.pop("team")

        name = d.pop("name")

        points = []
        _points = d.pop("points")
        for points_item_data in _points:
            points_item = ApiScoreSeriesPoint.from_dict(points_item_data)

            points.append(points_item)

        api_score_series = cls(
            team=team,
            name=name,
            points=points,
        )

        return api_score_series
