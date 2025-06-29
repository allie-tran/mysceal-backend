from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

from attrs import define as _attrs_define

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.api_client_answer import ApiClientAnswer


T = TypeVar("T", bound="ApiClientAnswerSet")


@_attrs_define
class ApiClientAnswerSet:
    """
    Attributes:
        answers (list['ApiClientAnswer']):
        task_id (Union[None, Unset, str]):
        task_name (Union[None, Unset, str]):
    """

    answers: list["ApiClientAnswer"]
    task_id: Union[None, Unset, str] = UNSET
    task_name: Union[None, Unset, str] = UNSET

    def to_dict(self) -> dict[str, Any]:
        answers = []
        for answers_item_data in self.answers:
            answers_item = answers_item_data.to_dict()
            answers.append(answers_item)

        task_id: Union[None, Unset, str]
        if isinstance(self.task_id, Unset):
            task_id = UNSET
        else:
            task_id = self.task_id

        task_name: Union[None, Unset, str]
        if isinstance(self.task_name, Unset):
            task_name = UNSET
        else:
            task_name = self.task_name

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "answers": answers,
            }
        )
        if task_id is not UNSET:
            field_dict["taskId"] = task_id
        if task_name is not UNSET:
            field_dict["taskName"] = task_name

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.api_client_answer import ApiClientAnswer

        d = dict(src_dict)
        answers = []
        _answers = d.pop("answers")
        for answers_item_data in _answers:
            answers_item = ApiClientAnswer.from_dict(answers_item_data)

            answers.append(answers_item)

        def _parse_task_id(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        task_id = _parse_task_id(d.pop("taskId", UNSET))

        def _parse_task_name(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        task_name = _parse_task_name(d.pop("taskName", UNSET))

        api_client_answer_set = cls(
            answers=answers,
            task_id=task_id,
            task_name=task_name,
        )

        return api_client_answer_set
