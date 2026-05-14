import asyncio
import base64
import hashlib
import secrets

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


def _pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(96)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).decode().rstrip("=")
    return verifier, challenge


@router.get("/google")
async def google_login(request: Request):
    flow = _create_flow()
    code_verifier, code_challenge = _pkce_pair()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )
    request.session["oauth_state"] = state
    request.session["oauth_code_verifier"] = code_verifier
    return RedirectResponse(auth_url)


@router.get("/google/callback")
async def google_callback(request: Request, code: str, state: str):
    import httpx
    from google.oauth2.credentials import Credentials

    stored_state = request.session.pop("oauth_state", None)
    if stored_state != state:
        return RedirectResponse(f"{settings.frontend_url}?error=state_mismatch")

    code_verifier = request.session.pop("oauth_code_verifier", None)

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
                **({"code_verifier": code_verifier} if code_verifier else {}),
            },
        )
    token_data = token_resp.json()
    if "error" in token_data:
        return RedirectResponse(f"{settings.frontend_url}?error=token_error")

    credentials = Credentials(
        token=token_data["access_token"],
        refresh_token=token_data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=SCOPES,
    )

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

    # Sync Google Classroom courses and enrollments for this user
    try:
        await _sync_courses(client, user.id)
    except Exception:
        pass  # Don't block login if classroom sync fails

    return RedirectResponse(settings.frontend_url)


async def _sync_courses(client: ClassroomAPIClient, user_id) -> None:
    from datetime import datetime, timezone
    from sqlalchemy import select
    from app.models.course import Course, CourseEnrollment

    now = datetime.now(timezone.utc)

    # Fetch teacher and student courses separately to determine role correctly
    teacher_courses, student_courses = await asyncio.gather(
        client.list_courses(teacher_id="me"),
        client.list_courses(student_id="me"),
    )
    courses_by_role = [(c, "teacher") for c in teacher_courses] + [(c, "student") for c in student_courses]

    async with AsyncSessionFactory() as session:
        for c, role in courses_by_role:
            classroom_id = c["id"]

            result = await session.execute(
                select(Course).where(Course.classroom_course_id == classroom_id)
            )
            course = result.scalar_one_or_none()
            if course is None:
                course = Course(
                    classroom_course_id=classroom_id,
                    name=c.get("name", ""),
                    section=c.get("section"),
                    synced_at=now,
                )
                session.add(course)
                await session.flush()
            else:
                course.name = c.get("name", "")
                course.section = c.get("section")
                course.synced_at = now

            enroll_result = await session.execute(
                select(CourseEnrollment).where(
                    CourseEnrollment.course_id == course.id,
                    CourseEnrollment.user_id == user_id,
                )
            )
            enrollment = enroll_result.scalar_one_or_none()
            if enrollment is None:
                session.add(CourseEnrollment(
                    course_id=course.id,
                    user_id=user_id,
                    role=role,
                    synced_at=now,
                ))
            else:
                enrollment.role = role
                enrollment.synced_at = now

        await session.commit()


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
