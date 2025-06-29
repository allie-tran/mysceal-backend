from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union

from attrs import define as _attrs_define

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.api_client_answer import ApiClientAnswer


T = TypeVar("T", bound="RankedAnswer")


@_attrs_define
class RankedAnswer:
    """
    Attributes:
        answer (ApiClientAnswer):
        rank (Union[Unset, int]):
    """

    answer: "ApiClientAnswer"
    rank: Union[Unset, int] = UNSET

    def to_dict(self) -> dict[str, Any]:
        answer = self.answer.to_dict()

        rank = self.rank

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "answer": answer,
            }
        )
        if rank is not UNSET:
            field_dict["rank"] = rank

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.api_client_answer import ApiClientAnswer

        d = dict(src_dict)
        answer = ApiClientAnswer.from_dict(d.pop("answer"))

        rank = d.pop("rank", UNSET)

        ranked_answer = cls(
            answer=answer,
            rank=rank,
        )

        return ranked_answer
