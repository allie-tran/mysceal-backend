from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.api_client_evaluation_info import ApiClientEvaluationInfo
from ...models.error_status import ErrorStatus
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    session: Union[Unset, str] = UNSET,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["session"] = session

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v2/client/evaluation/list",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[ErrorStatus, list["ApiClientEvaluationInfo"]]]:
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in _response_200:
            response_200_item = ApiClientEvaluationInfo.from_dict(response_200_item_data)

            response_200.append(response_200_item)

        return response_200
    if response.status_code == 401:
        response_401 = ErrorStatus.from_dict(response.json())

        return response_401
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[Union[ErrorStatus, list["ApiClientEvaluationInfo"]]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    session: Union[Unset, str] = UNSET,
) -> Response[Union[ErrorStatus, list["ApiClientEvaluationInfo"]]]:
    """Lists an overview of all evaluation runs visible to the current client.

    Args:
        session (Union[Unset, str]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorStatus, list['ApiClientEvaluationInfo']]]
    """

    kwargs = _get_kwargs(
        session=session,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: Union[AuthenticatedClient, Client],
    session: Union[Unset, str] = UNSET,
) -> Optional[Union[ErrorStatus, list["ApiClientEvaluationInfo"]]]:
    """Lists an overview of all evaluation runs visible to the current client.

    Args:
        session (Union[Unset, str]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorStatus, list['ApiClientEvaluationInfo']]
    """

    return sync_detailed(
        client=client,
        session=session,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    session: Union[Unset, str] = UNSET,
) -> Response[Union[ErrorStatus, list["ApiClientEvaluationInfo"]]]:
    """Lists an overview of all evaluation runs visible to the current client.

    Args:
        session (Union[Unset, str]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorStatus, list['ApiClientEvaluationInfo']]]
    """

    kwargs = _get_kwargs(
        session=session,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    session: Union[Unset, str] = UNSET,
) -> Optional[Union[ErrorStatus, list["ApiClientEvaluationInfo"]]]:
    """Lists an overview of all evaluation runs visible to the current client.

    Args:
        session (Union[Unset, str]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorStatus, list['ApiClientEvaluationInfo']]
    """

    return (
        await asyncio_detailed(
            client=client,
            session=session,
        )
    ).parsed
