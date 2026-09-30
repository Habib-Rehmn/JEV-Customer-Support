from fastapi import APIRouter, HTTPException, status

from app.api.deps import AdminUser, CurrentUser, SessionDep
from app.repositories.users import UserRepository
from app.schemas.auth import LoginRequest, TokenResponse, UserCreate, UserRead, UserUpdate
from app.services.auth_service import AuthService, EmailTaken, InvalidCredentials, LastAdmin, UserNotFound

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=TokenResponse)
async def login(data: LoginRequest, session: SessionDep):
    try:
        token, user = await AuthService(session).login(data.email, data.password)
    except InvalidCredentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    return TokenResponse(access_token=token, user=user)


@router.get("/auth/me", response_model=UserRead)
async def me(user: CurrentUser):
    return user


@router.get("/users", response_model=list[UserRead])
async def list_users(session: SessionDep, _: AdminUser):
    return await UserRepository(session).list()


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(data: UserCreate, session: SessionDep, _: AdminUser):
    try:
        return await AuthService(session).create_user(data)
    except EmailTaken:
        raise HTTPException(status.HTTP_409_CONFLICT, "A user with this email already exists")


@router.patch("/users/{user_id}", response_model=UserRead)
async def update_user(user_id: int, data: UserUpdate, session: SessionDep, _: AdminUser):
    try:
        return await AuthService(session).update_user(user_id, data)
    except UserNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    except LastAdmin:
        raise HTTPException(status.HTTP_409_CONFLICT, "There must be at least one admin")
