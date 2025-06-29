from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define

if TYPE_CHECKING:
    from ..models.api_client_answer_set import ApiClientAnswerSet


T = TypeVar("T", bound="ApiClientSubmission")


@_attrs_define
class ApiClientSubmission:
    """
    Attributes:
        answer_sets (list['ApiClientAnswerSet']):
    """

    answer_sets: list["ApiClientAnswerSet"]

    def to_dict(self) -> dict[str, Any]:
        answer_sets = []
        for answer_sets_item_data in self.answer_sets:
            answer_sets_item = answer_sets_item_data.to_dict()
            answer_sets.append(answer_sets_item)

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "answerSets": answer_sets,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.api_client_answer_set import ApiClientAnswerSet

        d = dict(src_dict)
        answer_sets = []
        _answer_sets = d.pop("answerSets")
        for answer_sets_item_data in _answer_sets:
            answer_sets_item = ApiClientAnswerSet.from_dict(answer_sets_item_data)

            answer_sets.append(answer_sets_item)

        api_client_submission = cls(
            answer_sets=answer_sets,
        )

        return api_client_submission
