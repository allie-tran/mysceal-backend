from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define

from ..models.api_evaluation_type import ApiEvaluationType

if TYPE_CHECKING:
    from ..models.api_run_properties import ApiRunProperties


T = TypeVar("T", bound="ApiEvaluationStartMessage")


@_attrs_define
class ApiEvaluationStartMessage:
    """
    Attributes:
        template_id (str):
        name (str):
        type_ (ApiEvaluationType):
        properties (ApiRunProperties):
    """

    template_id: str
    name: str
    type_: ApiEvaluationType
    properties: "ApiRunProperties"

    def to_dict(self) -> dict[str, Any]:
        template_id = self.template_id

        name = self.name

        type_ = self.type_.value

        properties = self.properties.to_dict()

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "templateId": template_id,
                "name": name,
                "type": type_,
                "properties": properties,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.api_run_properties import ApiRunProperties

        d = dict(src_dict)
        template_id = d.pop("templateId")

        name = d.pop("name")

        type_ = ApiEvaluationType(d.pop("type"))

        properties = ApiRunProperties.from_dict(d.pop("properties"))

        api_evaluation_start_message = cls(
            template_id=template_id,
            name=name,
            type_=type_,
            properties=properties,
        )

        return api_evaluation_start_message
