from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.api_evaluation_state import ApiEvaluationState
from ...models.error_status import ErrorStatus
from ...types import Response


def _get_kwargs(
    evaluation_id: str,
) -> dict[str, Any]:
    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": f"/api/v2/evaluation/{evaluation_id}/state",
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[ApiEvaluationState, ErrorStatus]]:
    if response.status_code == 200:
        response_200 = ApiEvaluationState.from_dict(response.json())

        return response_200
    if response.status_code == 401:
        response_401 = ErrorStatus.from_dict(response.json())

        return response_401
    if response.status_code == 403:
        response_403 = ErrorStatus.from_dict(response.json())

        return response_403
    if response.status_code == 404:
        response_404 = ErrorStatus.from_dict(response.json())

        return response_404
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[Union[ApiEvaluationState, ErrorStatus]]:
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
) -> Response[Union[ApiEvaluationState, ErrorStatus]]:
    """Returns the state of a specific evaluation.

    Args:
        evaluation_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ApiEvaluationState, ErrorStatus]]
    """

    kwargs = _get_kwargs(
        evaluation_id=evaluation_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    evaluation_id: str,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Optional[Union[ApiEvaluationState, ErrorStatus]]:
    """Returns the state of a specific evaluation.

    Args:
        evaluation_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ApiEvaluationState, ErrorStatus]
    """

    return sync_detailed(
        evaluation_id=evaluation_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    evaluation_id: str,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Response[Union[ApiEvaluationState, ErrorStatus]]:
    """Returns the state of a specific evaluation.

    Args:
        evaluation_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ApiEvaluationState, ErrorStatus]]
    """

    kwargs = _get_kwargs(
        evaluation_id=evaluation_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    evaluation_id: str,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Optional[Union[ApiEvaluationState, ErrorStatus]]:
    """Returns the state of a specific evaluation.

    Args:
        evaluation_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ApiEvaluationState, ErrorStatus]
    """

    return (
        await asyncio_detailed(
            evaluation_id=evaluation_id,
            client=client,
        )
    ).parsed
