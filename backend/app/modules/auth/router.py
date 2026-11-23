from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.dependencies import ClientIp, get_auth_service
from app.modules.auth.schemas import RegisterRequest
from app.modules.auth.service import AuthService
from app.modules.users.schemas import UserMeResponse

router = APIRouter(prefix="/auth", tags=["auth"])

AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


@router.post(
    "/register",
    response_model=UserMeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: RegisterRequest,
    ip: ClientIp,
    service: AuthServiceDep,
) -> UserMeResponse:
    user = await service.register(payload, ip=ip)
    return UserMeResponse.model_validate(user)
