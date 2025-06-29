from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define

T = TypeVar("T", bound="ApiJudgementValidatorStatus")


@_attrs_define
class ApiJudgementValidatorStatus:
    """
    Attributes:
        validator_name (str):
        pending (int):
        open_ (int):
    """

    validator_name: str
    pending: int
    open_: int

    def to_dict(self) -> dict[str, Any]:
        validator_name = self.validator_name

        pending = self.pending

        open_ = self.open_

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "validatorName": validator_name,
                "pending": pending,
                "open": open_,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        validator_name = d.pop("validatorName")

        pending = d.pop("pending")

        open_ = d.pop("open")

        api_judgement_validator_status = cls(
            validator_name=validator_name,
            pending=pending,
            open_=open_,
        )

        return api_judgement_validator_status
