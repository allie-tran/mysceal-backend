from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define

if TYPE_CHECKING:
    from ..models.api_task_overview import ApiTaskOverview


T = TypeVar("T", bound="ApiTeamTaskOverview")


@_attrs_define
class ApiTeamTaskOverview:
    """
    Attributes:
        team_id (str):
        tasks (list['ApiTaskOverview']):
    """

    team_id: str
    tasks: list["ApiTaskOverview"]

    def to_dict(self) -> dict[str, Any]:
        team_id = self.team_id

        tasks = []
        for tasks_item_data in self.tasks:
            tasks_item = tasks_item_data.to_dict()
            tasks.append(tasks_item)

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "teamId": team_id,
                "tasks": tasks,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.api_task_overview import ApiTaskOverview

        d = dict(src_dict)
        team_id = d.pop("teamId")

        tasks = []
        _tasks = d.pop("tasks")
        for tasks_item_data in _tasks:
            tasks_item = ApiTaskOverview.from_dict(tasks_item_data)

            tasks.append(tasks_item)

        api_team_task_overview = cls(
            team_id=team_id,
            tasks=tasks,
        )

        return api_team_task_overview
