from collections.abc import Mapping
from typing import Any, TypeVar, Union

from attrs import define as _attrs_define

from ..types import UNSET, Unset

T = TypeVar("T", bound="ApiTaskTemplateInfo")


@_attrs_define
class ApiTaskTemplateInfo:
    """
    Attributes:
        template_id (str):
        name (str):
        task_group (str):
        task_type (str):
        duration (int):
        comment (Union[Unset, str]):
    """

    template_id: str
    name: str
    task_group: str
    task_type: str
    duration: int
    comment: Union[Unset, str] = UNSET

    def to_dict(self) -> dict[str, Any]:
        template_id = self.template_id

        name = self.name

        task_group = self.task_group

        task_type = self.task_type

        duration = self.duration

        comment = self.comment

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "templateId": template_id,
                "name": name,
                "taskGroup": task_group,
                "taskType": task_type,
                "duration": duration,
            }
        )
        if comment is not UNSET:
            field_dict["comment"] = comment

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        template_id = d.pop("templateId")

        name = d.pop("name")

        task_group = d.pop("taskGroup")

        task_type = d.pop("taskType")

        duration = d.pop("duration")

        comment = d.pop("comment", UNSET)

        api_task_template_info = cls(
            template_id=template_id,
            name=name,
            task_group=task_group,
            task_type=task_type,
            duration=duration,
            comment=comment,
        )

        return api_task_template_info
