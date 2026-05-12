from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow

from app.core.config import settings
from app.core.database import AsyncSessionFactory
from app.core.security import decrypt_token, encrypt_token
from app.services.classroom_api import ClassroomAPIClient

router = APIRouter()

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.coursework.students",
    "https://www.googleapis.com/auth/classroom.rosters.readonly",
    "https://www.googleapis.com/auth/classroom.profile.emails",
]


def _create_flow() -> Flow:
    return Flow.from_client_config(
        {
            "web": {
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uris": [settings.google_redirect_uri],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        redirect_uri=settings.google_redirect_uri,
    )


@router.get("/google")
async def google_login(request: Request):
    flow = _create_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    request.session["oauth_state"] = state
    code_verifier = getattr(flow.oauth2session, "_code_verifier", None)
    if code_verifier:
        request.session["oauth_code_verifier"] = code_verifier
    return RedirectResponse(auth_url)


@router.get("/google/callback")
async def google_callback(request: Request, code: str, state: str):
    stored_state = request.session.pop("oauth_state", None)
    if stored_state != state:
        return RedirectResponse(f"{settings.frontend_url}?error=state_mismatch")

    flow = _create_flow()
    code_verifier = request.session.pop("oauth_code_verifier", None)
    fetch_kwargs: dict = {"code": code}
    if code_verifier:
        fetch_kwargs["code_verifier"] = code_verifier
    flow.fetch_token(**fetch_kwargs)
    credentials = flow.credentials

    client = ClassroomAPIClient(credentials)
    profile = await client.get_user_profile()

    async with AsyncSessionFactory() as session:
        from sqlalchemy import select
        from app.models.user import User

        result = await session.execute(
            select(User).where(User.google_id == profile["id"])
        )
        user = result.scalar_one_or_none()

        encrypted_rt = encrypt_token(credentials.refresh_token) if credentials.refresh_token else None

        if user is None:
            user = User(
                google_id=profile["id"],
                email=profile["email"],
                name=profile["name"],
                profile_picture_url=profile.get("picture"),
                encrypted_refresh_token=encrypted_rt,
            )
            session.add(user)
        else:
            user.name = profile["name"]
            user.profile_picture_url = profile.get("picture")
            if encrypted_rt:
                user.encrypted_refresh_token = encrypted_rt
        await session.commit()
        await session.refresh(user)

    request.session["user_id"] = str(user.id)
    return RedirectResponse(settings.frontend_url)


@router.post("/logout")
async def logout(request: Request, response: Response):
    request.session.clear()
    return {"ok": True}


@router.get("/me")
async def get_me(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Not authenticated")

    async with AsyncSessionFactory() as session:
        from sqlalchemy import select
        from app.models.user import User
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="User not found")

    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "profile_picture_url": user.profile_picture_url,
    }
