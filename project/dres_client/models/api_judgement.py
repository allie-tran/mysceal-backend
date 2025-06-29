from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define

from ..models.api_verdict_status import ApiVerdictStatus

T = TypeVar("T", bound="ApiJudgement")


@_attrs_define
class ApiJudgement:
    """
    Attributes:
        token (str):
        validator (str):
        verdict (ApiVerdictStatus):
    """

    token: str
    validator: str
    verdict: ApiVerdictStatus

    def to_dict(self) -> dict[str, Any]:
        token = self.token

        validator = self.validator

        verdict = self.verdict.value

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "token": token,
                "validator": validator,
                "verdict": verdict,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        token = d.pop("token")

        validator = d.pop("validator")

        verdict = ApiVerdictStatus(d.pop("verdict"))

        api_judgement = cls(
            token=token,
            validator=validator,
            verdict=verdict,
        )

        return api_judgement
