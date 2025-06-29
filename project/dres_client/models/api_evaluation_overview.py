from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define

from ..models.run_manager_status import RunManagerStatus

if TYPE_CHECKING:
    from ..models.api_team_task_overview import ApiTeamTaskOverview


T = TypeVar("T", bound="ApiEvaluationOverview")


@_attrs_define
class ApiEvaluationOverview:
    """
    Attributes:
        state (RunManagerStatus):
        team_overviews (list['ApiTeamTaskOverview']):
    """

    state: RunManagerStatus
    team_overviews: list["ApiTeamTaskOverview"]

    def to_dict(self) -> dict[str, Any]:
        state = self.state.value

        team_overviews = []
        for team_overviews_item_data in self.team_overviews:
            team_overviews_item = team_overviews_item_data.to_dict()
            team_overviews.append(team_overviews_item)

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "state": state,
                "teamOverviews": team_overviews,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.api_team_task_overview import ApiTeamTaskOverview

        d = dict(src_dict)
        state = RunManagerStatus(d.pop("state"))

        team_overviews = []
        _team_overviews = d.pop("teamOverviews")
        for team_overviews_item_data in _team_overviews:
            team_overviews_item = ApiTeamTaskOverview.from_dict(team_overviews_item_data)

            team_overviews.append(team_overviews_item)

        api_evaluation_overview = cls(
            state=state,
            team_overviews=team_overviews,
        )

        return api_evaluation_overview
