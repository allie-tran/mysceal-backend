from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define

if TYPE_CHECKING:
    from ..models.api_answer_set import ApiAnswerSet


T = TypeVar("T", bound="ApiSubmission")


@_attrs_define
class ApiSubmission:
    """
    Attributes:
        submission_id (str):
        team_id (str):
        member_id (str):
        team_name (str):
        member_name (str):
        timestamp (int):
        answers (list['ApiAnswerSet']):
    """

    submission_id: str
    team_id: str
    member_id: str
    team_name: str
    member_name: str
    timestamp: int
    answers: list["ApiAnswerSet"]

    def to_dict(self) -> dict[str, Any]:
        submission_id = self.submission_id

        team_id = self.team_id

        member_id = self.member_id

        team_name = self.team_name

        member_name = self.member_name

        timestamp = self.timestamp

        answers = []
        for answers_item_data in self.answers:
            answers_item = answers_item_data.to_dict()
            answers.append(answers_item)

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "submissionId": submission_id,
                "teamId": team_id,
                "memberId": member_id,
                "teamName": team_name,
                "memberName": member_name,
                "timestamp": timestamp,
                "answers": answers,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.api_answer_set import ApiAnswerSet

        d = dict(src_dict)
        submission_id = d.pop("submissionId")

        team_id = d.pop("teamId")

        member_id = d.pop("memberId")

        team_name = d.pop("teamName")

        member_name = d.pop("memberName")

        timestamp = d.pop("timestamp")

        answers = []
        _answers = d.pop("answers")
        for answers_item_data in _answers:
            answers_item = ApiAnswerSet.from_dict(answers_item_data)

            answers.append(answers_item)

        api_submission = cls(
            submission_id=submission_id,
            team_id=team_id,
            member_id=member_id,
            team_name=team_name,
            member_name=member_name,
            timestamp=timestamp,
            answers=answers,
        )

        return api_submission
