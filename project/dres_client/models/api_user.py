from collections.abc import Mapping
from typing import Any, TypeVar, Union

from attrs import define as _attrs_define

from ..models.api_role import ApiRole
from ..types import UNSET, Unset

T = TypeVar("T", bound="ApiUser")


@_attrs_define
class ApiUser:
    """
    Attributes:
        id (Union[Unset, str]):
        username (Union[Unset, str]):
        role (Union[Unset, ApiRole]):
        session_id (Union[Unset, str]):
    """

    id: Union[Unset, str] = UNSET
    username: Union[Unset, str] = UNSET
    role: Union[Unset, ApiRole] = UNSET
    session_id: Union[Unset, str] = UNSET

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        username = self.username

        role: Union[Unset, str] = UNSET
        if not isinstance(self.role, Unset):
            role = self.role.value

        session_id = self.session_id

        field_dict: dict[str, Any] = {}

        field_dict.update({})
        if id is not UNSET:
            field_dict["id"] = id
        if username is not UNSET:
            field_dict["username"] = username
        if role is not UNSET:
            field_dict["role"] = role
        if session_id is not UNSET:
            field_dict["sessionId"] = session_id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id", UNSET)

        username = d.pop("username", UNSET)

        _role = d.pop("role", UNSET)
        role: Union[Unset, ApiRole]
        if isinstance(_role, Unset):
            role = UNSET
        else:
            role = ApiRole(_role)

        session_id = d.pop("sessionId", UNSET)

        api_user = cls(
            id=id,
            username=username,
            role=role,
            session_id=session_id,
        )

        return api_user
