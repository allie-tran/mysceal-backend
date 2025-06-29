from collections.abc import Mapping
from typing import Any, TypeVar, Union

from attrs import define as _attrs_define

from ..models.api_role import ApiRole
from ..types import UNSET, Unset

T = TypeVar("T", bound="ApiUserRequest")


@_attrs_define
class ApiUserRequest:
    """
    Attributes:
        username (str):
        password (Union[Unset, str]):
        role (Union[Unset, ApiRole]):
    """

    username: str
    password: Union[Unset, str] = UNSET
    role: Union[Unset, ApiRole] = UNSET

    def to_dict(self) -> dict[str, Any]:
        username = self.username

        password = self.password

        role: Union[Unset, str] = UNSET
        if not isinstance(self.role, Unset):
            role = self.role.value

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "username": username,
            }
        )
        if password is not UNSET:
            field_dict["password"] = password
        if role is not UNSET:
            field_dict["role"] = role

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        username = d.pop("username")

        password = d.pop("password", UNSET)

        _role = d.pop("role", UNSET)
        role: Union[Unset, ApiRole]
        if isinstance(_role, Unset):
            role = UNSET
        else:
            role = ApiRole(_role)

        api_user_request = cls(
            username=username,
            password=password,
            role=role,
        )

        return api_user_request
