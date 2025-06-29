from collections.abc import Mapping
from typing import Any, TypeVar, Union

from attrs import define as _attrs_define

from ..types import UNSET, Unset

T = TypeVar("T", bound="ApiEvaluationTemplateOverview")


@_attrs_define
class ApiEvaluationTemplateOverview:
    """
    Attributes:
        id (str):
        name (str):
        task_count (int):
        team_count (int):
        description (Union[Unset, str]):
    """

    id: str
    name: str
    task_count: int
    team_count: int
    description: Union[Unset, str] = UNSET

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        name = self.name

        task_count = self.task_count

        team_count = self.team_count

        description = self.description

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "id": id,
                "name": name,
                "taskCount": task_count,
                "teamCount": team_count,
            }
        )
        if description is not UNSET:
            field_dict["description"] = description

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id")

        name = d.pop("name")

        task_count = d.pop("taskCount")

        team_count = d.pop("teamCount")

        description = d.pop("description", UNSET)

        api_evaluation_template_overview = cls(
            id=id,
            name=name,
            task_count=task_count,
            team_count=team_count,
            description=description,
        )

        return api_evaluation_template_overview
