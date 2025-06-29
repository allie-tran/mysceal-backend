from collections.abc import Mapping
from typing import Any, TypeVar, Union

from attrs import define as _attrs_define

from ..models.api_evaluation_status import ApiEvaluationStatus
from ..models.api_task_status import ApiTaskStatus
from ..types import UNSET, Unset

T = TypeVar("T", bound="ApiEvaluationState")


@_attrs_define
class ApiEvaluationState:
    """
    Attributes:
        evaluation_id (str):
        evaluation_status (ApiEvaluationStatus):
        task_status (ApiTaskStatus):
        time_left (int):
        time_elapsed (int):
        task_id (Union[Unset, str]):
        task_template_id (Union[Unset, str]):
    """

    evaluation_id: str
    evaluation_status: ApiEvaluationStatus
    task_status: ApiTaskStatus
    time_left: int
    time_elapsed: int
    task_id: Union[Unset, str] = UNSET
    task_template_id: Union[Unset, str] = UNSET

    def to_dict(self) -> dict[str, Any]:
        evaluation_id = self.evaluation_id

        evaluation_status = self.evaluation_status.value

        task_status = self.task_status.value

        time_left = self.time_left

        time_elapsed = self.time_elapsed

        task_id = self.task_id

        task_template_id = self.task_template_id

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "evaluationId": evaluation_id,
                "evaluationStatus": evaluation_status,
                "taskStatus": task_status,
                "timeLeft": time_left,
                "timeElapsed": time_elapsed,
            }
        )
        if task_id is not UNSET:
            field_dict["taskId"] = task_id
        if task_template_id is not UNSET:
            field_dict["taskTemplateId"] = task_template_id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        evaluation_id = d.pop("evaluationId")

        evaluation_status = ApiEvaluationStatus(d.pop("evaluationStatus"))

        task_status = ApiTaskStatus(d.pop("taskStatus"))

        time_left = d.pop("timeLeft")

        time_elapsed = d.pop("timeElapsed")

        task_id = d.pop("taskId", UNSET)

        task_template_id = d.pop("taskTemplateId", UNSET)

        api_evaluation_state = cls(
            evaluation_id=evaluation_id,
            evaluation_status=evaluation_status,
            task_status=task_status,
            time_left=time_left,
            time_elapsed=time_elapsed,
            task_id=task_id,
            task_template_id=task_template_id,
        )

        return api_evaluation_state
