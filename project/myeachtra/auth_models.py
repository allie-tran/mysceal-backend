import os
from typing import Dict, List

import bcrypt
import jwt
import redis
from configs import DRES_URL, REDIS_HOST, REDIS_PORT
from database.main import user_collection
from dres_client import Client
from dres_client.api.user import post_api_v2_login
from dres_client.models import LoginRequest as DRESLoginRequest
from dres_client.models.api_user import ApiUser
from dres_client.models.error_status import ErrorStatus
from fastapi import HTTPException, Request
from query_parse.types.requests import (
    CreateUserRequest,
    Data,
    LoginRequest,
    LoginResponse,
)
from rich import print

from myeachtra.dependencies import CamelCaseModel

SECRET = os.getenv("JWT_SECRET", "")
assert SECRET, "JWT_SECRET is not set"


class UserDetail(CamelCaseModel):
    username: str
    data_access: List[Data] = [Data.LSC23]


# Remove all redis keys
def flush_redis() -> None:
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    r.flushall()
    print("Redis flushed")


# flush_redis()
def create_user(request: CreateUserRequest, overwrite=False) -> None:
    """
    Create a new user
    """
    if user_collection.find_one({"username": request.username}) and not overwrite:
        raise HTTPException(status_code=400, detail="User already exists")

    user_collection.update_one(
        {"username": request.username},
        {
            "$set": {
                "password": bcrypt.hashpw(request.password.encode(), bcrypt.gensalt()),
                "data_access": request.data_access,
                "dres": request.dres,
            }
        },
        upsert=True,
    )
    print(f"User {request.username} created")


# Create some users now
def create_users() -> None:
    # admin = CreateUserRequest(
    #     username=os.getenv("ADMIN_USERNAME", ""),
    #     password=os.getenv("ADMIN_PASSWORD", ""),
    #     data_access=[Data.LSC23, Data.Deakin],
    # )
    # create_user(admin, overwrite=True)
    pass

create_users()


def generate_token(username: str, dres_token: str | None = None) -> str:
    """
    Generate a token for the user
    """
    return jwt.encode(
        {"username": username, "dres_token": dres_token}, SECRET, algorithm="HS256"
    )


def find_user_by_username(username: str) -> UserDetail:
    """
    Find a user by username
    """
    user = user_collection.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=401, detail="User does not exist")
    return UserDetail(**user)


def verify_user(request: LoginRequest) -> LoginResponse:
    """
    Verify user credentials and return an access token
    """
    user = user_collection.find_one({"username": request.username})
    if not user:
        raise HTTPException(status_code=401, detail="User does not exist")
    if bcrypt.checkpw(request.password.encode(), user["password"]):
        if request.dres or user.get("dres", False):
            print("DRES login requested")
            client = Client(base_url=DRES_URL)
            with client as client:
                response = post_api_v2_login.sync_detailed(
                    client=client,
                    body=DRESLoginRequest(
                        username=request.username, password=request.password
                    ),
                )
                if response.status_code == 200:
                    if isinstance(response.parsed, ApiUser):
                        dres_session_id = str(response.parsed.session_id)
                        return LoginResponse(
                            data_access=user["data_access"],
                            session_id=generate_token(
                                request.username, dres_token=dres_session_id
                            ),
                            dres_session_id=dres_session_id,
                        )
                elif isinstance(response.parsed, ErrorStatus):
                    raise HTTPException(
                        status_code=401,
                        detail=f"DRES login failed with {response.parsed.description}",
                    )
                else:
                    raise HTTPException(status_code=401, detail="DRES login failed")
        return LoginResponse(
            data_access=user["data_access"],
            session_id=generate_token(request.username),
        )
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")


def verify_token(token: str) -> Dict[str, str | None]:
    """
    Verify the token and return the username
    """
    try:
        data = jwt.decode(token, SECRET, algorithms=["HS256"])
        if "username" not in data:
            raise HTTPException(status_code=401, detail="Invalid token")
        return data
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token is expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_user(request: Request) -> UserDetail:
    """
    Get the user from the request to make sure the user is authenticated
    """
    token = request.headers.get("Authorization")  # Bearer token
    if not token:
        raise HTTPException(status_code=401, detail="Please log in")
    username = verify_token(token.split(" ")[1])["username"]
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = find_user_by_username(username)
    request_data = await request.json()
    verify_data_access(Data(request_data["data"]), user)
    return user


def verify_data_access(data: Data, user: UserDetail) -> None:
    """
    Verify the user has access to the data
    """
    if data not in user.data_access:
        raise HTTPException(
            status_code=403, detail="User does not have access to this data"
        )
