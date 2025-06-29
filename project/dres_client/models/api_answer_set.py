from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define

from ..models.api_verdict_status import ApiVerdictStatus

if TYPE_CHECKING:
    from ..models.api_answer import ApiAnswer


T = TypeVar("T", bound="ApiAnswerSet")


@_attrs_define
class ApiAnswerSet:
    """
    Attributes:
        id (str):
        status (ApiVerdictStatus):
        task_id (str):
        answers (list['ApiAnswer']):
    """

    id: str
    status: ApiVerdictStatus
    task_id: str
    answers: list["ApiAnswer"]

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        status = self.status.value

        task_id = self.task_id

        answers = []
        for answers_item_data in self.answers:
            answers_item = answers_item_data.to_dict()
            answers.append(answers_item)

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "id": id,
                "status": status,
                "taskId": task_id,
                "answers": answers,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.api_answer import ApiAnswer

        d = dict(src_dict)
        id = d.pop("id")

        status = ApiVerdictStatus(d.pop("status"))

        task_id = d.pop("taskId")

        answers = []
        _answers = d.pop("answers")
        for answers_item_data in _answers:
            answers_item = ApiAnswer.from_dict(answers_item_data)

            answers.append(answers_item)

        api_answer_set = cls(
            id=id,
            status=status,
            task_id=task_id,
            answers=answers,
        )

        return api_answer_set
