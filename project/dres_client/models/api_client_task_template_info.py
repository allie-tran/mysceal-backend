from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define

T = TypeVar("T", bound="ApiClientTaskTemplateInfo")


@_attrs_define
class ApiClientTaskTemplateInfo:
    """
    Attributes:
        name (str):
        task_group (str):
        task_type (str):
        duration (int):
    """

    name: str
    task_group: str
    task_type: str
    duration: int

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        task_group = self.task_group

        task_type = self.task_type

        duration = self.duration

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "name": name,
                "taskGroup": task_group,
                "taskType": task_type,
                "duration": duration,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        name = d.pop("name")

        task_group = d.pop("taskGroup")

        task_type = d.pop("taskType")

        duration = d.pop("duration")

        api_client_task_template_info = cls(
            name=name,
            task_group=task_group,
            task_type=task_type,
            duration=duration,
        )

        return api_client_task_template_info
