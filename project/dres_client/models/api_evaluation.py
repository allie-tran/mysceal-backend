from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union

from attrs import define as _attrs_define

from ..models.api_evaluation_type import ApiEvaluationType
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.api_evaluation_template import ApiEvaluationTemplate
    from ..models.api_task import ApiTask


T = TypeVar("T", bound="ApiEvaluation")


@_attrs_define
class ApiEvaluation:
    """
    Attributes:
        evaluation_id (str):
        name (str):
        type_ (ApiEvaluationType):
        template (ApiEvaluationTemplate):
        created (int):
        tasks (list['ApiTask']):
        started (Union[Unset, int]):
        ended (Union[Unset, int]):
    """

    evaluation_id: str
    name: str
    type_: ApiEvaluationType
    template: "ApiEvaluationTemplate"
    created: int
    tasks: list["ApiTask"]
    started: Union[Unset, int] = UNSET
    ended: Union[Unset, int] = UNSET

    def to_dict(self) -> dict[str, Any]:
        evaluation_id = self.evaluation_id

        name = self.name

        type_ = self.type_.value

        template = self.template.to_dict()

        created = self.created

        tasks = []
        for tasks_item_data in self.tasks:
            tasks_item = tasks_item_data.to_dict()
            tasks.append(tasks_item)

        started = self.started

        ended = self.ended

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "evaluationId": evaluation_id,
                "name": name,
                "type": type_,
                "template": template,
                "created": created,
                "tasks": tasks,
            }
        )
        if started is not UNSET:
            field_dict["started"] = started
        if ended is not UNSET:
            field_dict["ended"] = ended

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.api_evaluation_template import ApiEvaluationTemplate
        from ..models.api_task import ApiTask

        d = dict(src_dict)
        evaluation_id = d.pop("evaluationId")

        name = d.pop("name")

        type_ = ApiEvaluationType(d.pop("type"))

        template = ApiEvaluationTemplate.from_dict(d.pop("template"))

        created = d.pop("created")

        tasks = []
        _tasks = d.pop("tasks")
        for tasks_item_data in _tasks:
            tasks_item = ApiTask.from_dict(tasks_item_data)

            tasks.append(tasks_item)

        started = d.pop("started", UNSET)

        ended = d.pop("ended", UNSET)

        api_evaluation = cls(
            evaluation_id=evaluation_id,
            name=name,
            type_=type_,
            template=template,
            created=created,
            tasks=tasks,
            started=started,
            ended=ended,
        )

        return api_evaluation
