
from dres_client.client import AuthenticatedClient
from dres_client.models.api_answer import ApiAnswer
from dres_client.api.submission import post_api_v2_submit_by_evaluation_id
from dres_client.models.api_answer_set import ApiAnswerSet
from dres_client.models.api_client_answer_set import ApiClientAnswerSet
from dres_client.models.api_client_submission import ApiClientSubmission


# def submit_image(image: str, client: AuthenticatedClient):
#     """
#     Submit an image to the DRES service.
#     :param image: The image file path or URL to submit.
#     :param client: An authenticated DRES client instance.
#     :return: Response from the DRES service.
#     """
#     with client as client:
#         response = post_api_v2_submit_by_evaluation_id.sync_detailed(
#             client=client,
#             evaluation_id="default_evaluation",  # Replace with actual evaluation ID
#             body=ApiClientSubmission(
#                 answer_sets=[
#                     ApiClientAnswerSet(
#                         taskId=

#                 ]
#             )
#         )

