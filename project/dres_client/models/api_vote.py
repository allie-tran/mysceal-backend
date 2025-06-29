from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define

from ..models.api_verdict_status import ApiVerdictStatus

T = TypeVar("T", bound="ApiVote")


@_attrs_define
class ApiVote:
    """
    Attributes:
        verdict (ApiVerdictStatus):
    """

    verdict: ApiVerdictStatus

    def to_dict(self) -> dict[str, Any]:
        verdict = self.verdict.value

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "verdict": verdict,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        verdict = ApiVerdictStatus(d.pop("verdict"))

        api_vote = cls(
            verdict=verdict,
        )

        return api_vote
