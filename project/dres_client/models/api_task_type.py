from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define

from ..models.api_hint_option import ApiHintOption
from ..models.api_score_option import ApiScoreOption
from ..models.api_submission_option import ApiSubmissionOption
from ..models.api_target_option import ApiTargetOption
from ..models.api_task_option import ApiTaskOption

if TYPE_CHECKING:
    from ..models.api_task_type_configuration import ApiTaskTypeConfiguration


T = TypeVar("T", bound="ApiTaskType")


@_attrs_define
class ApiTaskType:
    """
    Attributes:
        name (str):
        duration (int):
        target_option (ApiTargetOption):
        hint_options (list[ApiHintOption]):
        submission_options (list[ApiSubmissionOption]):
        task_options (list[ApiTaskOption]):
        score_option (ApiScoreOption):
        configuration (ApiTaskTypeConfiguration):
    """

    name: str
    duration: int
    target_option: ApiTargetOption
    hint_options: list[ApiHintOption]
    submission_options: list[ApiSubmissionOption]
    task_options: list[ApiTaskOption]
    score_option: ApiScoreOption
    configuration: "ApiTaskTypeConfiguration"

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        duration = self.duration

        target_option = self.target_option.value

        hint_options = []
        for hint_options_item_data in self.hint_options:
            hint_options_item = hint_options_item_data.value
            hint_options.append(hint_options_item)

        submission_options = []
        for submission_options_item_data in self.submission_options:
            submission_options_item = submission_options_item_data.value
            submission_options.append(submission_options_item)

        task_options = []
        for task_options_item_data in self.task_options:
            task_options_item = task_options_item_data.value
            task_options.append(task_options_item)

        score_option = self.score_option.value

        configuration = self.configuration.to_dict()

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "name": name,
                "duration": duration,
                "targetOption": target_option,
                "hintOptions": hint_options,
                "submissionOptions": submission_options,
                "taskOptions": task_options,
                "scoreOption": score_option,
                "configuration": configuration,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.api_task_type_configuration import ApiTaskTypeConfiguration

        d = dict(src_dict)
        name = d.pop("name")

        duration = d.pop("duration")

        target_option = ApiTargetOption(d.pop("targetOption"))

        hint_options = []
        _hint_options = d.pop("hintOptions")
        for hint_options_item_data in _hint_options:
            hint_options_item = ApiHintOption(hint_options_item_data)

            hint_options.append(hint_options_item)

        submission_options = []
        _submission_options = d.pop("submissionOptions")
        for submission_options_item_data in _submission_options:
            submission_options_item = ApiSubmissionOption(submission_options_item_data)

            submission_options.append(submission_options_item)

        task_options = []
        _task_options = d.pop("taskOptions")
        for task_options_item_data in _task_options:
            task_options_item = ApiTaskOption(task_options_item_data)

            task_options.append(task_options_item)

        score_option = ApiScoreOption(d.pop("scoreOption"))

        configuration = ApiTaskTypeConfiguration.from_dict(d.pop("configuration"))

        api_task_type = cls(
            name=name,
            duration=duration,
            target_option=target_option,
            hint_options=hint_options,
            submission_options=submission_options,
            task_options=task_options,
            score_option=score_option,
            configuration=configuration,
        )

        return api_task_type
