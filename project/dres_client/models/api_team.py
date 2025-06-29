from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union

from attrs import define as _attrs_define

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.api_user import ApiUser


T = TypeVar("T", bound="ApiTeam")


@_attrs_define
class ApiTeam:
    """
    Attributes:
        users (list['ApiUser']):
        team_id (str):
        id (Union[Unset, str]):
        name (Union[Unset, str]):
        color (Union[Unset, str]):
        logo_data (Union[Unset, str]):
    """

    users: list["ApiUser"]
    team_id: str
    id: Union[Unset, str] = UNSET
    name: Union[Unset, str] = UNSET
    color: Union[Unset, str] = UNSET
    logo_data: Union[Unset, str] = UNSET

    def to_dict(self) -> dict[str, Any]:
        users = []
        for users_item_data in self.users:
            users_item = users_item_data.to_dict()
            users.append(users_item)

        team_id = self.team_id

        id = self.id

        name = self.name

        color = self.color

        logo_data = self.logo_data

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "users": users,
                "teamId": team_id,
            }
        )
        if id is not UNSET:
            field_dict["id"] = id
        if name is not UNSET:
            field_dict["name"] = name
        if color is not UNSET:
            field_dict["color"] = color
        if logo_data is not UNSET:
            field_dict["logoData"] = logo_data

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.api_user import ApiUser

        d = dict(src_dict)
        users = []
        _users = d.pop("users")
        for users_item_data in _users:
            users_item = ApiUser.from_dict(users_item_data)

            users.append(users_item)

        team_id = d.pop("teamId")

        id = d.pop("id", UNSET)

        name = d.pop("name", UNSET)

        color = d.pop("color", UNSET)

        logo_data = d.pop("logoData", UNSET)

        api_team = cls(
            users=users,
            team_id=team_id,
            id=id,
            name=name,
            color=color,
            logo_data=logo_data,
        )

        return api_team
