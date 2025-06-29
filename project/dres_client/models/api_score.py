from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define

T = TypeVar("T", bound="ApiScore")


@_attrs_define
class ApiScore:
    """
    Attributes:
        team_id (str):
        score (float):
    """

    team_id: str
    score: float

    def to_dict(self) -> dict[str, Any]:
        team_id = self.team_id

        score = self.score

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "teamId": team_id,
                "score": score,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        team_id = d.pop("teamId")

        score = d.pop("score")

        api_score = cls(
            team_id=team_id,
            score=score,
        )

        return api_score
