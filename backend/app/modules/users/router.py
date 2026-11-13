import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.dependencies import (  # CurrentUser será implementado no módulo auth
    CurrentUser,
    get_user_service,
)
from app.modules.users.schemas import (
    ActivateNutritionistProfileRequest,
    ActivateStudentProfileRequest,
    ActivateTrainerProfileRequest,
    PublicUserResponse,
    UpdateProfileRequest,
    UserMeResponse,
)
from app.modules.users.service import UserService

router = APIRouter(prefix="/users", tags=["users"])

UserServiceDep = Annotated[UserService, Depends(get_user_service)]


@router.get("/me", response_model=UserMeResponse, status_code=status.HTTP_200_OK)
async def get_me(
    current_user: CurrentUser,
    service: UserServiceDep,
) -> UserMeResponse:
    user = await service.get_user_by_id(current_user.id, load_profiles=True)
    return UserMeResponse.model_validate(user)


@router.patch("/me", response_model=UserMeResponse, status_code=status.HTTP_200_OK)
async def update_me(
    payload: UpdateProfileRequest,
    current_user: CurrentUser,
    service: UserServiceDep,
) -> UserMeResponse:
    raw_data = payload.model_dump(exclude_unset=True)
    update_altura_cm = "altura_cm" in payload.model_fields_set
    altura_cm = raw_data.pop("altura_cm", None)
    condicoes_saude = raw_data.pop("condicoes_saude", None)

    user = await service.update_profile(
        current_user.id,
        user_fields=raw_data,
        altura_cm=altura_cm,
        update_altura_cm=update_altura_cm,
        condicoes_saude=condicoes_saude,
    )
    return UserMeResponse.model_validate(user)


@router.post(
    "/me/profiles/student",
    response_model=UserMeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def activate_student_profile(
    payload: ActivateStudentProfileRequest,
    current_user: CurrentUser,
    service: UserServiceDep,
) -> UserMeResponse:
    user = await service.activate_student_profile(
        current_user.id,
        altura_cm=payload.altura_cm,
    )
    return UserMeResponse.model_validate(user)


@router.post(
    "/me/profiles/trainer",
    response_model=UserMeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def activate_trainer_profile(
    payload: ActivateTrainerProfileRequest,
    current_user: CurrentUser,
    service: UserServiceDep,
) -> UserMeResponse:
    user = await service.activate_trainer_profile(
        current_user.id,
        cref=payload.cref,
    )
    return UserMeResponse.model_validate(user)


@router.post(
    "/me/profiles/nutritionist",
    response_model=UserMeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def activate_nutritionist_profile(
    payload: ActivateNutritionistProfileRequest,
    current_user: CurrentUser,
    service: UserServiceDep,
) -> UserMeResponse:
    user = await service.activate_nutritionist_profile(
        current_user.id,
        crn=payload.crn,
    )
    return UserMeResponse.model_validate(user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    current_user: CurrentUser,
    service: UserServiceDep,
) -> None:
    await service.delete_account(current_user.id)


@router.get(
    "/{user_id}",
    response_model=PublicUserResponse,
    status_code=status.HTTP_200_OK,
)
async def get_public_user(
    user_id: uuid.UUID,
    _current_user: CurrentUser,
    service: UserServiceDep,
) -> PublicUserResponse:
    user = await service.get_user_by_id(user_id, load_profiles=True)
    return PublicUserResponse.model_validate(user)