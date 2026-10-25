from typing import Optional

from src.users.dependencies import UserServiceDep
from fastapi import APIRouter, Request, status
from src.auth.dependencies import CurrentUserDep

from src.users.v1.schemas import UserResponse, UserCreate
from src.rate_limiting import limiter

router = APIRouter(prefix="/api/v1/users", tags=["users"])

@router.post(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    description="Creates user profile record in database.",
    responses={
        409: {"detail": "User profile already exists"}
    }
)
@limiter.limit("5/second")
async def create_me(request: Request, current_user: CurrentUserDep, service: UserServiceDep, data: Optional[UserCreate] = None):
    if data is None:
        data = UserCreate()
    
    profile = await service.create_my_profile(
        current_user, 
        full_name=data.full_name, 
        phone=data.phone
    )
    
    return UserResponse.parse_from_user(current_user, profile)

@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    description="Returns user profile record if it exists.",
    responses={
        404: {"detail": "User profile not found."}
    }
)
@limiter.limit("5/minute")
async def get_me(request: Request, current_user: CurrentUserDep, service: UserServiceDep):
    profile = await service.get_my_profile(current_user)
    return UserResponse.parse_from_user(current_user, profile) 
