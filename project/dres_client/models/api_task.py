from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union

from attrs import define as _attrs_define

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.api_submission import ApiSubmission


T = TypeVar("T", bound="ApiTask")


@_attrs_define
class ApiTask:
    """
    Attributes:
        task_id (str):
        template_id (str):
        submissions (list['ApiSubmission']):
        started (Union[Unset, int]):
        ended (Union[Unset, int]):
    """

    task_id: str
    template_id: str
    submissions: list["ApiSubmission"]
    started: Union[Unset, int] = UNSET
    ended: Union[Unset, int] = UNSET

    def to_dict(self) -> dict[str, Any]:
        task_id = self.task_id

        template_id = self.template_id

        submissions = []
        for submissions_item_data in self.submissions:
            submissions_item = submissions_item_data.to_dict()
            submissions.append(submissions_item)

        started = self.started

        ended = self.ended

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "taskId": task_id,
                "templateId": template_id,
                "submissions": submissions,
            }
        )
        if started is not UNSET:
            field_dict["started"] = started
        if ended is not UNSET:
            field_dict["ended"] = ended

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.api_submission import ApiSubmission

        d = dict(src_dict)
        task_id = d.pop("taskId")

        template_id = d.pop("templateId")

        submissions = []
        _submissions = d.pop("submissions")
        for submissions_item_data in _submissions:
            submissions_item = ApiSubmission.from_dict(submissions_item_data)

            submissions.append(submissions_item)

        started = d.pop("started", UNSET)

        ended = d.pop("ended", UNSET)

        api_task = cls(
            task_id=task_id,
            template_id=template_id,
            submissions=submissions,
            started=started,
            ended=ended,
        )

        return api_task
