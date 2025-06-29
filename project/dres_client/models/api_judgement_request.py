from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union

from attrs import define as _attrs_define

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.api_answer_set import ApiAnswerSet


T = TypeVar("T", bound="ApiJudgementRequest")


@_attrs_define
class ApiJudgementRequest:
    """
    Attributes:
        validator (str):
        task_description (str):
        answer_set (ApiAnswerSet):
        token (Union[Unset, str]):
    """

    validator: str
    task_description: str
    answer_set: "ApiAnswerSet"
    token: Union[Unset, str] = UNSET

    def to_dict(self) -> dict[str, Any]:
        validator = self.validator

        task_description = self.task_description

        answer_set = self.answer_set.to_dict()

        token = self.token

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "validator": validator,
                "taskDescription": task_description,
                "answerSet": answer_set,
            }
        )
        if token is not UNSET:
            field_dict["token"] = token

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.api_answer_set import ApiAnswerSet

        d = dict(src_dict)
        validator = d.pop("validator")

        task_description = d.pop("taskDescription")

        answer_set = ApiAnswerSet.from_dict(d.pop("answerSet"))

        token = d.pop("token", UNSET)

        api_judgement_request = cls(
            validator=validator,
            task_description=task_description,
            answer_set=answer_set,
            token=token,
        )

        return api_judgement_request
