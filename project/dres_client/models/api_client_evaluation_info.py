from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

from attrs import define as _attrs_define

from ..models.api_evaluation_status import ApiEvaluationStatus
from ..models.api_evaluation_type import ApiEvaluationType
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.api_client_task_template_info import ApiClientTaskTemplateInfo


T = TypeVar("T", bound="ApiClientEvaluationInfo")


@_attrs_define
class ApiClientEvaluationInfo:
    """
    Attributes:
        id (str):
        name (str):
        type_ (ApiEvaluationType):
        status (ApiEvaluationStatus):
        template_id (str):
        teams (list[str]):
        task_templates (list['ApiClientTaskTemplateInfo']):
        template_description (Union[Unset, str]):
    """

    id: str
    name: str
    type_: ApiEvaluationType
    status: ApiEvaluationStatus
    template_id: str
    teams: list[str]
    task_templates: list["ApiClientTaskTemplateInfo"]
    template_description: Union[Unset, str] = UNSET

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        name = self.name

        type_ = self.type_.value

        status = self.status.value

        template_id = self.template_id

        teams = self.teams

        task_templates = []
        for task_templates_item_data in self.task_templates:
            task_templates_item = task_templates_item_data.to_dict()
            task_templates.append(task_templates_item)

        template_description = self.template_description

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "id": id,
                "name": name,
                "type": type_,
                "status": status,
                "templateId": template_id,
                "teams": teams,
                "taskTemplates": task_templates,
            }
        )
        if template_description is not UNSET:
            field_dict["templateDescription"] = template_description

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.api_client_task_template_info import ApiClientTaskTemplateInfo

        d = dict(src_dict)
        id = d.pop("id")

        name = d.pop("name")

        type_ = ApiEvaluationType(d.pop("type"))

        status = ApiEvaluationStatus(d.pop("status"))

        template_id = d.pop("templateId")

        teams = cast(list[str], d.pop("teams"))

        task_templates = []
        _task_templates = d.pop("taskTemplates")
        for task_templates_item_data in _task_templates:
            task_templates_item = ApiClientTaskTemplateInfo.from_dict(task_templates_item_data)

            task_templates.append(task_templates_item)

        template_description = d.pop("templateDescription", UNSET)

        api_client_evaluation_info = cls(
            id=id,
            name=name,
            type_=type_,
            status=status,
            template_id=template_id,
            teams=teams,
            task_templates=task_templates,
            template_description=template_description,
        )

        return api_client_evaluation_info
