from collections.abc import Mapping
from typing import Any, TypeVar, Union

from attrs import define as _attrs_define

from ..models.api_task_status import ApiTaskStatus
from ..types import UNSET, Unset

T = TypeVar("T", bound="ApiTaskOverview")


@_attrs_define
class ApiTaskOverview:
    """
    Attributes:
        id (str):
        name (str):
        type_ (str):
        group (str):
        duration (int):
        task_id (str):
        status (ApiTaskStatus):
        started (Union[Unset, int]):
        ended (Union[Unset, int]):
    """

    id: str
    name: str
    type_: str
    group: str
    duration: int
    task_id: str
    status: ApiTaskStatus
    started: Union[Unset, int] = UNSET
    ended: Union[Unset, int] = UNSET

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        name = self.name

        type_ = self.type_

        group = self.group

        duration = self.duration

        task_id = self.task_id

        status = self.status.value

        started = self.started

        ended = self.ended

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "id": id,
                "name": name,
                "type": type_,
                "group": group,
                "duration": duration,
                "taskId": task_id,
                "status": status,
            }
        )
        if started is not UNSET:
            field_dict["started"] = started
        if ended is not UNSET:
            field_dict["ended"] = ended

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id")

        name = d.pop("name")

        type_ = d.pop("type")

        group = d.pop("group")

        duration = d.pop("duration")

        task_id = d.pop("taskId")

        status = ApiTaskStatus(d.pop("status"))

        started = d.pop("started", UNSET)

        ended = d.pop("ended", UNSET)

        api_task_overview = cls(
            id=id,
            name=name,
            type_=type_,
            group=group,
            duration=duration,
            task_id=task_id,
            status=status,
            started=started,
            ended=ended,
        )

        return api_task_overview
