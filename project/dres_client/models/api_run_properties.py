from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define

T = TypeVar("T", bound="ApiRunProperties")


@_attrs_define
class ApiRunProperties:
    """
    Attributes:
        participant_can_view (bool):
        shuffle_tasks (bool):
        allow_repeated_tasks (bool):
        limit_submission_previews (int):
    """

    participant_can_view: bool
    shuffle_tasks: bool
    allow_repeated_tasks: bool
    limit_submission_previews: int

    def to_dict(self) -> dict[str, Any]:
        participant_can_view = self.participant_can_view

        shuffle_tasks = self.shuffle_tasks

        allow_repeated_tasks = self.allow_repeated_tasks

        limit_submission_previews = self.limit_submission_previews

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "participantCanView": participant_can_view,
                "shuffleTasks": shuffle_tasks,
                "allowRepeatedTasks": allow_repeated_tasks,
                "limitSubmissionPreviews": limit_submission_previews,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        participant_can_view = d.pop("participantCanView")

        shuffle_tasks = d.pop("shuffleTasks")

        allow_repeated_tasks = d.pop("allowRepeatedTasks")

        limit_submission_previews = d.pop("limitSubmissionPreviews")

        api_run_properties = cls(
            participant_can_view=participant_can_view,
            shuffle_tasks=shuffle_tasks,
            allow_repeated_tasks=allow_repeated_tasks,
            limit_submission_previews=limit_submission_previews,
        )

        return api_run_properties
