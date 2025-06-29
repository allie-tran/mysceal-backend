from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.api_user import ApiUser
from ...models.api_user_request import ApiUserRequest
from ...models.error_status import ErrorStatus
from ...types import Response


def _get_kwargs(
    *,
    body: ApiUserRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v2/user",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[ApiUser, ErrorStatus]]:
    if response.status_code == 200:
        response_200 = ApiUser.from_dict(response.json())

        return response_200
    if response.status_code == 400:
        response_400 = ErrorStatus.from_dict(response.json())

        return response_400
    if response.status_code == 500:
        response_500 = ErrorStatus.from_dict(response.json())

        return response_500
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[Union[ApiUser, ErrorStatus]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: ApiUserRequest,
) -> Response[Union[ApiUser, ErrorStatus]]:
    """Creates a new user, if the username is not already taken. Requires ADMIN privileges

    Args:
        body (ApiUserRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ApiUser, ErrorStatus]]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: Union[AuthenticatedClient, Client],
    body: ApiUserRequest,
) -> Optional[Union[ApiUser, ErrorStatus]]:
    """Creates a new user, if the username is not already taken. Requires ADMIN privileges

    Args:
        body (ApiUserRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ApiUser, ErrorStatus]
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: ApiUserRequest,
) -> Response[Union[ApiUser, ErrorStatus]]:
    """Creates a new user, if the username is not already taken. Requires ADMIN privileges

    Args:
        body (ApiUserRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ApiUser, ErrorStatus]]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    body: ApiUserRequest,
) -> Optional[Union[ApiUser, ErrorStatus]]:
    """Creates a new user, if the username is not already taken. Requires ADMIN privileges

    Args:
        body (ApiUserRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ApiUser, ErrorStatus]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
