from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_status import ErrorStatus
from ...models.query_event_log import QueryEventLog
from ...models.success_status import SuccessStatus
from ...types import UNSET, Response


def _get_kwargs(
    evaluation_id: str,
    *,
    body: QueryEventLog,
    session: str,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    params: dict[str, Any] = {}

    params["session"] = session

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": f"/api/v2/log/query/{evaluation_id}",
        "params": params,
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[ErrorStatus, SuccessStatus]]:
    if response.status_code == 200:
        response_200 = SuccessStatus.from_dict(response.json())

        return response_200
    if response.status_code == 400:
        response_400 = ErrorStatus.from_dict(response.json())

        return response_400
    if response.status_code == 401:
        response_401 = ErrorStatus.from_dict(response.json())

        return response_401
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[Union[ErrorStatus, SuccessStatus]]:
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
    body: QueryEventLog,
    session: str,
) -> Response[Union[ErrorStatus, SuccessStatus]]:
    """Accepts query logs from participants for the specified evaluation.

    Args:
        evaluation_id (str):
        session (str):
        body (QueryEventLog):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorStatus, SuccessStatus]]
    """

    kwargs = _get_kwargs(
        evaluation_id=evaluation_id,
        body=body,
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
    body: QueryEventLog,
    session: str,
) -> Optional[Union[ErrorStatus, SuccessStatus]]:
    """Accepts query logs from participants for the specified evaluation.

    Args:
        evaluation_id (str):
        session (str):
        body (QueryEventLog):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorStatus, SuccessStatus]
    """

    return sync_detailed(
        evaluation_id=evaluation_id,
        client=client,
        body=body,
        session=session,
    ).parsed


async def asyncio_detailed(
    evaluation_id: str,
    *,
    client: Union[AuthenticatedClient, Client],
    body: QueryEventLog,
    session: str,
) -> Response[Union[ErrorStatus, SuccessStatus]]:
    """Accepts query logs from participants for the specified evaluation.

    Args:
        evaluation_id (str):
        session (str):
        body (QueryEventLog):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorStatus, SuccessStatus]]
    """

    kwargs = _get_kwargs(
        evaluation_id=evaluation_id,
        body=body,
        session=session,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    evaluation_id: str,
    *,
    client: Union[AuthenticatedClient, Client],
    body: QueryEventLog,
    session: str,
) -> Optional[Union[ErrorStatus, SuccessStatus]]:
    """Accepts query logs from participants for the specified evaluation.

    Args:
        evaluation_id (str):
        session (str):
        body (QueryEventLog):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorStatus, SuccessStatus]
    """

    return (
        await asyncio_detailed(
            evaluation_id=evaluation_id,
            client=client,
            body=body,
            session=session,
        )
    ).parsed
