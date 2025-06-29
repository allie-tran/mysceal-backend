from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.api_client_task_template_info import ApiClientTaskTemplateInfo
from ...models.error_status import ErrorStatus
from ...types import UNSET, Response, Unset


def _get_kwargs(
    evaluation_id: str,
    *,
    session: Union[Unset, str] = UNSET,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["session"] = session

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": f"/api/v2/client/evaluation/currentTask/{evaluation_id}",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[ApiClientTaskTemplateInfo, ErrorStatus]]:
    if response.status_code == 200:
        response_200 = ApiClientTaskTemplateInfo.from_dict(response.json())

        return response_200
    if response.status_code == 401:
        response_401 = ErrorStatus.from_dict(response.json())

        return response_401
    if response.status_code == 404:
        response_404 = ErrorStatus.from_dict(response.json())

        return response_404
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[Union[ApiClientTaskTemplateInfo, ErrorStatus]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    evaluation_id: str,
    *,
    client: Union[AuthenticatedClient, Client],
    session: Union[Unset, str] = UNSET,
) -> Response[Union[ApiClientTaskTemplateInfo, ErrorStatus]]:
    """Returns an overview of the currently active task for a run.

    Args:
        evaluation_id (str):
        session (Union[Unset, str]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ApiClientTaskTemplateInfo, ErrorStatus]]
    """

    kwargs = _get_kwargs(
        evaluation_id=evaluation_id,
        session=session,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    evaluation_id: str,
    *,
    client: Union[AuthenticatedClient, Client],
    session: Union[Unset, str] = UNSET,
) -> Optional[Union[ApiClientTaskTemplateInfo, ErrorStatus]]:
    """Returns an overview of the currently active task for a run.

    Args:
        evaluation_id (str):
        session (Union[Unset, str]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ApiClientTaskTemplateInfo, ErrorStatus]
    """

    return sync_detailed(
        evaluation_id=evaluation_id,
        client=client,
        session=session,
    ).parsed


async def asyncio_detailed(
    evaluation_id: str,
    *,
    client: Union[AuthenticatedClient, Client],
    session: Union[Unset, str] = UNSET,
) -> Response[Union[ApiClientTaskTemplateInfo, ErrorStatus]]:
    """Returns an overview of the currently active task for a run.

    Args:
        evaluation_id (str):
        session (Union[Unset, str]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ApiClientTaskTemplateInfo, ErrorStatus]]
    """

    kwargs = _get_kwargs(
        evaluation_id=evaluation_id,
        session=session,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    evaluation_id: str,
    *,
    client: Union[AuthenticatedClient, Client],
    session: Union[Unset, str] = UNSET,
) -> Optional[Union[ApiClientTaskTemplateInfo, ErrorStatus]]:
    """Returns an overview of the currently active task for a run.

    Args:
        evaluation_id (str):
        session (Union[Unset, str]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ApiClientTaskTemplateInfo, ErrorStatus]
    """

    return (
        await asyncio_detailed(
            evaluation_id=evaluation_id,
            client=client,
            session=session,
        )
    ).parsed
