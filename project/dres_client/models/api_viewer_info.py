from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define

T = TypeVar("T", bound="ApiViewerInfo")


@_attrs_define
class ApiViewerInfo:
    """
    Attributes:
        viewers_id (str):
        username (str):
        host (str):
        ready (bool):
    """

    viewers_id: str
    username: str
    host: str
    ready: bool

    def to_dict(self) -> dict[str, Any]:
        viewers_id = self.viewers_id

        username = self.username

        host = self.host

        ready = self.ready

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "viewersId": viewers_id,
                "username": username,
                "host": host,
                "ready": ready,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        viewers_id = d.pop("viewersId")

        username = d.pop("username")

        host = d.pop("host")

        ready = d.pop("ready")

        api_viewer_info = cls(
            viewers_id=viewers_id,
            username=username,
            host=host,
            ready=ready,
        )

        return api_viewer_info
