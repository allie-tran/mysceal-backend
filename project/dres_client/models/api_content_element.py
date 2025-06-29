from collections.abc import Mapping
from typing import Any, TypeVar, Union

from attrs import define as _attrs_define

from ..models.api_content_type import ApiContentType
from ..types import UNSET, Unset

T = TypeVar("T", bound="ApiContentElement")


@_attrs_define
class ApiContentElement:
    """
    Attributes:
        content_type (ApiContentType):
        offset (int):
        content (Union[Unset, str]):
    """

    content_type: ApiContentType
    offset: int
    content: Union[Unset, str] = UNSET

    def to_dict(self) -> dict[str, Any]:
        content_type = self.content_type.value

        offset = self.offset

        content = self.content

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "contentType": content_type,
                "offset": offset,
            }
        )
        if content is not UNSET:
            field_dict["content"] = content

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        content_type = ApiContentType(d.pop("contentType"))

        offset = d.pop("offset")

        content = d.pop("content", UNSET)

        api_content_element = cls(
            content_type=content_type,
            offset=offset,
            content=content,
        )

        return api_content_element
