from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union

from attrs import define as _attrs_define

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.api_score import ApiScore


T = TypeVar("T", bound="ApiScoreOverview")


@_attrs_define
class ApiScoreOverview:
    """
    Attributes:
        name (str):
        scores (list['ApiScore']):
        task_group (Union[Unset, str]):
    """

    name: str
    scores: list["ApiScore"]
    task_group: Union[Unset, str] = UNSET

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        scores = []
        for scores_item_data in self.scores:
            scores_item = scores_item_data.to_dict()
            scores.append(scores_item)

        task_group = self.task_group

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "name": name,
                "scores": scores,
            }
        )
        if task_group is not UNSET:
            field_dict["taskGroup"] = task_group

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.api_score import ApiScore

        d = dict(src_dict)
        name = d.pop("name")

        scores = []
        _scores = d.pop("scores")
        for scores_item_data in _scores:
            scores_item = ApiScore.from_dict(scores_item_data)

            scores.append(scores_item)

        task_group = d.pop("taskGroup", UNSET)

        api_score_overview = cls(
            name=name,
            scores=scores,
            task_group=task_group,
        )

        return api_score_overview
