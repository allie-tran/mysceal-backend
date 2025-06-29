from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define

if TYPE_CHECKING:
    from ..models.api_content_element import ApiContentElement


T = TypeVar("T", bound="ApiTargetContent")


@_attrs_define
class ApiTargetContent:
    """
    Attributes:
        task_id (str):
        sequence (list['ApiContentElement']):
    """

    task_id: str
    sequence: list["ApiContentElement"]

    def to_dict(self) -> dict[str, Any]:
        task_id = self.task_id

        sequence = []
        for sequence_item_data in self.sequence:
            sequence_item = sequence_item_data.to_dict()
            sequence.append(sequence_item)

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "taskId": task_id,
                "sequence": sequence,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.api_content_element import ApiContentElement

        d = dict(src_dict)
        task_id = d.pop("taskId")

        sequence = []
        _sequence = d.pop("sequence")
        for sequence_item_data in _sequence:
            sequence_item = ApiContentElement.from_dict(sequence_item_data)

            sequence.append(sequence_item)

        api_target_content = cls(
            task_id=task_id,
            sequence=sequence,
        )

        return api_target_content
