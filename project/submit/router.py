import json
import httpx
from dres_client.api.submission import post_api_v2_submit_by_evaluation_id
from dres_client.client import AuthenticatedClient
from dres_client.models.api_client_answer import ApiClientAnswer
from dres_client.models.api_client_answer_set import ApiClientAnswerSet
from dres_client.models.api_client_submission import ApiClientSubmission
from fastapi import APIRouter, Depends, HTTPException, Request
from myeachtra.auth_models import get_user, verify_token
from rich import print

from submit.models import DRESSubmitResponse, SubmitAnswerRequest, SubmitAnswerResponse

submit_router = APIRouter()

from configs import DRES_URL
from dres_client import AuthenticatedClient


def get_dres_client(request: Request) -> AuthenticatedClient:
    """
    Get the user from the request to make sure the user is authenticated
    """
    token = request.headers.get("Authorization")  # Bearer token
    if not token:
        raise HTTPException(status_code=401, detail="Please log in")
    data = verify_token(token.split(" ")[1])
    dres_token = data.get("dres_token", None)
    if dres_token:
        return AuthenticatedClient(
            base_url=DRES_URL,
            token=dres_token,
            httpx_args={"params": {"session": dres_token}},
        )
    raise HTTPException(status_code=401, detail="Please log in with DRES credentials")


@submit_router.post(
    "/submit-answer",
    response_model=SubmitAnswerResponse,
    dependencies=[Depends(get_dres_client), Depends(get_user)],
)
async def submit_answer(
    request: SubmitAnswerRequest,
    dres_client: AuthenticatedClient = Depends(get_dres_client),
):
    """
    Submit an answer to DRES
    """
    if request.query_type == "QA":
        answer = ApiClientAnswer(text=request.answer)
    else:
        answer = ApiClientAnswer(
            media_item_name=request.answer.split('.')[0].split("/")[-1],
        )

    dres_response = post_api_v2_submit_by_evaluation_id.sync_detailed(
        client=dres_client,
        evaluation_id=request.evaluation_id,
        body=ApiClientSubmission(
            answer_sets=[
                ApiClientAnswerSet(
                    task_id="",
                    task_name="",
                    answers=[answer],
                )
            ],
        ),
    )

    #         url = f"{SUBMIT_URL}/{request.evaluation_id}?session={request.session_id}"
    #         dres_response = await client.post(
    #             url, json=dres_request.model_dump(by_alias=True, exclude_unset=True)
    #         )

    if dres_response.status_code != 200:
        print("DRES response error:", dres_response)
        return SubmitAnswerResponse(
            severity="warning",
            message=json.loads(dres_response.content).get("description", "Unknown error"),
            verdict="ERROR",
        )
    if not dres_response.parsed:
        print("DRES response is empty")
        return SubmitAnswerResponse(
            severity="error",
            message="DRES response is empty",
            verdict="ERROR",
        )

    response = DRESSubmitResponse.model_validate(dres_response.parsed.to_dict())
    print("Response", response.model_dump())

    match (response.status, response.submission):
        case (False, _):
            return SubmitAnswerResponse(
                severity="error",
                message=response.description,
                verdict="INVALID",
            )
        case (_, "INVALID"):
            return SubmitAnswerResponse(
                severity="error",
                message=response.description,
                verdict="INVALID",
            )
        case (_, "ERROR"):
            return SubmitAnswerResponse(
                severity="error",
                message=response.description,
                verdict="ERROR",
            )
        case (_, "CORRECT"):
            return SubmitAnswerResponse(
                severity="success",
                message=response.description,
                verdict="CORRECT",
            )
        case (_, x) if x in ["INCORRECT", "WRONG"]:
            return SubmitAnswerResponse(
                severity="warning",
                message=response.description,
                verdict="INCORRECT",
            )
        case (_, "INDETERMINATE"):
            return SubmitAnswerResponse(
                severity="info",
                message=response.description,
                verdict="INDETERMINATE",
            )
        case _:
            raise HTTPException(status_code=500, detail="Unknown response")
