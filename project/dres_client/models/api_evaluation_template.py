from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

from attrs import define as _attrs_define

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.api_task_group import ApiTaskGroup
    from ..models.api_task_template import ApiTaskTemplate
    from ..models.api_task_type import ApiTaskType
    from ..models.api_team import ApiTeam
    from ..models.api_team_group import ApiTeamGroup


T = TypeVar("T", bound="ApiEvaluationTemplate")


@_attrs_define
class ApiEvaluationTemplate:
    """
    Attributes:
        id (str):
        name (str):
        task_types (list['ApiTaskType']):
        task_groups (list['ApiTaskGroup']):
        tasks (list['ApiTaskTemplate']):
        teams (list['ApiTeam']):
        team_groups (list['ApiTeamGroup']):
        judges (list[str]):
        viewers (list[str]):
        description (Union[Unset, str]):
        created (Union[Unset, int]):
        modified (Union[Unset, int]):
    """

    id: str
    name: str
    task_types: list["ApiTaskType"]
    task_groups: list["ApiTaskGroup"]
    tasks: list["ApiTaskTemplate"]
    teams: list["ApiTeam"]
    team_groups: list["ApiTeamGroup"]
    judges: list[str]
    viewers: list[str]
    description: Union[Unset, str] = UNSET
    created: Union[Unset, int] = UNSET
    modified: Union[Unset, int] = UNSET

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        name = self.name

        task_types = []
        for task_types_item_data in self.task_types:
            task_types_item = task_types_item_data.to_dict()
            task_types.append(task_types_item)

        task_groups = []
        for task_groups_item_data in self.task_groups:
            task_groups_item = task_groups_item_data.to_dict()
            task_groups.append(task_groups_item)

        tasks = []
        for tasks_item_data in self.tasks:
            tasks_item = tasks_item_data.to_dict()
            tasks.append(tasks_item)

        teams = []
        for teams_item_data in self.teams:
            teams_item = teams_item_data.to_dict()
            teams.append(teams_item)

        team_groups = []
        for team_groups_item_data in self.team_groups:
            team_groups_item = team_groups_item_data.to_dict()
            team_groups.append(team_groups_item)

        judges = self.judges

        viewers = self.viewers

        description = self.description

        created = self.created

        modified = self.modified

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "id": id,
                "name": name,
                "taskTypes": task_types,
                "taskGroups": task_groups,
                "tasks": tasks,
                "teams": teams,
                "teamGroups": team_groups,
                "judges": judges,
                "viewers": viewers,
            }
        )
        if description is not UNSET:
            field_dict["description"] = description
        if created is not UNSET:
            field_dict["created"] = created
        if modified is not UNSET:
            field_dict["modified"] = modified

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.api_task_group import ApiTaskGroup
        from ..models.api_task_template import ApiTaskTemplate
        from ..models.api_task_type import ApiTaskType
        from ..models.api_team import ApiTeam
        from ..models.api_team_group import ApiTeamGroup

        d = dict(src_dict)
        id = d.pop("id")

        name = d.pop("name")

        task_types = []
        _task_types = d.pop("taskTypes")
        for task_types_item_data in _task_types:
            task_types_item = ApiTaskType.from_dict(task_types_item_data)

            task_types.append(task_types_item)

        task_groups = []
        _task_groups = d.pop("taskGroups")
        for task_groups_item_data in _task_groups:
            task_groups_item = ApiTaskGroup.from_dict(task_groups_item_data)

            task_groups.append(task_groups_item)

        tasks = []
        _tasks = d.pop("tasks")
        for tasks_item_data in _tasks:
            tasks_item = ApiTaskTemplate.from_dict(tasks_item_data)

            tasks.append(tasks_item)

        teams = []
        _teams = d.pop("teams")
        for teams_item_data in _teams:
            teams_item = ApiTeam.from_dict(teams_item_data)

            teams.append(teams_item)

        team_groups = []
        _team_groups = d.pop("teamGroups")
        for team_groups_item_data in _team_groups:
            team_groups_item = ApiTeamGroup.from_dict(team_groups_item_data)

            team_groups.append(team_groups_item)

        judges = cast(list[str], d.pop("judges"))

        viewers = cast(list[str], d.pop("viewers"))

        description = d.pop("description", UNSET)

        created = d.pop("created", UNSET)

        modified = d.pop("modified", UNSET)

        api_evaluation_template = cls(
            id=id,
            name=name,
            task_types=task_types,
            task_groups=task_groups,
            tasks=tasks,
            teams=teams,
            team_groups=team_groups,
            judges=judges,
            viewers=viewers,
            description=description,
            created=created,
            modified=modified,
        )

        return api_evaluation_template
