from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define

if TYPE_CHECKING:
    from ..models.api_submission import ApiSubmission


T = TypeVar("T", bound="ApiSubmissionInfo")


@_attrs_define
class ApiSubmissionInfo:
    """
    Attributes:
        evaluation_id (str):
        task_id (str):
        submissions (list['ApiSubmission']):
    """

    evaluation_id: str
    task_id: str
    submissions: list["ApiSubmission"]

    def to_dict(self) -> dict[str, Any]:
        evaluation_id = self.evaluation_id

        task_id = self.task_id

        submissions = []
        for submissions_item_data in self.submissions:
            submissions_item = submissions_item_data.to_dict()
            submissions.append(submissions_item)

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "evaluationId": evaluation_id,
                "taskId": task_id,
                "submissions": submissions,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.api_submission import ApiSubmission

        d = dict(src_dict)
        evaluation_id = d.pop("evaluationId")

        task_id = d.pop("taskId")

        submissions = []
        _submissions = d.pop("submissions")
        for submissions_item_data in _submissions:
            submissions_item = ApiSubmission.from_dict(submissions_item_data)

            submissions.append(submissions_item)

        api_submission_info = cls(
            evaluation_id=evaluation_id,
            task_id=task_id,
            submissions=submissions,
        )

        return api_submission_info
