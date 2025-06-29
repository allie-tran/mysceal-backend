from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union

from attrs import define as _attrs_define

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.api_hint import ApiHint
    from ..models.api_target import ApiTarget


T = TypeVar("T", bound="ApiTaskTemplate")


@_attrs_define
class ApiTaskTemplate:
    """
    Attributes:
        name (str):
        task_group (str):
        task_type (str):
        duration (int):
        collection_id (str):
        targets (list['ApiTarget']):
        hints (list['ApiHint']):
        id (Union[Unset, str]):
        comment (Union[Unset, str]):
    """

    name: str
    task_group: str
    task_type: str
    duration: int
    collection_id: str
    targets: list["ApiTarget"]
    hints: list["ApiHint"]
    id: Union[Unset, str] = UNSET
    comment: Union[Unset, str] = UNSET

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        task_group = self.task_group

        task_type = self.task_type

        duration = self.duration

        collection_id = self.collection_id

        targets = []
        for targets_item_data in self.targets:
            targets_item = targets_item_data.to_dict()
            targets.append(targets_item)

        hints = []
        for hints_item_data in self.hints:
            hints_item = hints_item_data.to_dict()
            hints.append(hints_item)

        id = self.id

        comment = self.comment

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "name": name,
                "taskGroup": task_group,
                "taskType": task_type,
                "duration": duration,
                "collectionId": collection_id,
                "targets": targets,
                "hints": hints,
            }
        )
        if id is not UNSET:
            field_dict["id"] = id
        if comment is not UNSET:
            field_dict["comment"] = comment

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.api_hint import ApiHint
        from ..models.api_target import ApiTarget

        d = dict(src_dict)
        name = d.pop("name")

        task_group = d.pop("taskGroup")

        task_type = d.pop("taskType")

        duration = d.pop("duration")

        collection_id = d.pop("collectionId")

        targets = []
        _targets = d.pop("targets")
        for targets_item_data in _targets:
            targets_item = ApiTarget.from_dict(targets_item_data)

            targets.append(targets_item)

        hints = []
        _hints = d.pop("hints")
        for hints_item_data in _hints:
            hints_item = ApiHint.from_dict(hints_item_data)

            hints.append(hints_item)

        id = d.pop("id", UNSET)

        comment = d.pop("comment", UNSET)

        api_task_template = cls(
            name=name,
            task_group=task_group,
            task_type=task_type,
            duration=duration,
            collection_id=collection_id,
            targets=targets,
            hints=hints,
            id=id,
            comment=comment,
        )

        return api_task_template
