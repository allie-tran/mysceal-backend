from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union

from attrs import define as _attrs_define

from ..models.api_team_aggregator_type import ApiTeamAggregatorType
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.api_team import ApiTeam


T = TypeVar("T", bound="ApiTeamGroup")


@_attrs_define
class ApiTeamGroup:
    """
    Attributes:
        teams (list['ApiTeam']):
        aggregation (ApiTeamAggregatorType):
        id (Union[Unset, str]):
        name (Union[Unset, str]):
    """

    teams: list["ApiTeam"]
    aggregation: ApiTeamAggregatorType
    id: Union[Unset, str] = UNSET
    name: Union[Unset, str] = UNSET

    def to_dict(self) -> dict[str, Any]:
        teams = []
        for teams_item_data in self.teams:
            teams_item = teams_item_data.to_dict()
            teams.append(teams_item)

        aggregation = self.aggregation.value

        id = self.id

        name = self.name

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "teams": teams,
                "aggregation": aggregation,
            }
        )
        if id is not UNSET:
            field_dict["id"] = id
        if name is not UNSET:
            field_dict["name"] = name

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.api_team import ApiTeam

        d = dict(src_dict)
        teams = []
        _teams = d.pop("teams")
        for teams_item_data in _teams:
            teams_item = ApiTeam.from_dict(teams_item_data)

            teams.append(teams_item)

        aggregation = ApiTeamAggregatorType(d.pop("aggregation"))

        id = d.pop("id", UNSET)

        name = d.pop("name", UNSET)

        api_team_group = cls(
            teams=teams,
            aggregation=aggregation,
            id=id,
            name=name,
        )

        return api_team_group
