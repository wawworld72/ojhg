"""GitHub OAuth integration and publish endpoints."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.github import GitHubIntegration, GitHubPublish, GitHubPublishStudentResult

router = APIRouter()


def _get_current_user_id(request: Request) -> uuid.UUID:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return uuid.UUID(user_id)


@router.get("/github/connect")
async def github_connect(request: Request):
    """Redirect teacher to GitHub OAuth."""
    from app.core.config import settings
    state = str(uuid.uuid4())
    request.session["github_oauth_state"] = state
    scope = "repo"
    url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.github_client_id}"
        f"&scope={scope}"
        f"&state={state}"
    )
    return RedirectResponse(url)


@router.get("/github/callback")
async def github_callback(
    code: str,
    state: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Exchange code for token and store encrypted in GitHubIntegration."""
    import httpx
    from app.core.config import settings
    from app.core.security import encrypt_token

    if state != request.session.get("github_oauth_state"):
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    user_id = _get_current_user_id(request)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            json={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
            },
        )
        resp.raise_for_status()
        token_data = resp.json()

    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="GitHub OAuth failed")

    async with httpx.AsyncClient() as client:
        user_resp = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"token {access_token}", "Accept": "application/vnd.github+json"},
        )
        user_resp.raise_for_status()
        github_user = user_resp.json()

    github_username = github_user["login"]
    encrypted_token = encrypt_token(access_token)

    result = await db.execute(
        select(GitHubIntegration).where(GitHubIntegration.teacher_id == user_id)
    )
    integration = result.scalar_one_or_none()

    if integration:
        integration.github_username = github_username
        integration.encrypted_access_token = encrypted_token
        integration.updated_at = datetime.now(timezone.utc)
    else:
        integration = GitHubIntegration(
            teacher_id=user_id,
            github_username=github_username,
            encrypted_access_token=encrypted_token,
            target_repo_name="ojhg-submissions",
        )
        db.add(integration)

    await db.commit()
    return RedirectResponse("/teacher/publish")


@router.get("/github/status")
async def github_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = _get_current_user_id(request)
    result = await db.execute(
        select(GitHubIntegration).where(GitHubIntegration.teacher_id == user_id)
    )
    integration = result.scalar_one_or_none()
    if not integration:
        return {"connected": False}
    return {
        "connected": True,
        "github_username": integration.github_username,
        "target_repo_name": integration.target_repo_name,
    }


@router.post("/assignments/{assignment_id}/publish", status_code=202)
async def publish_assignment(
    assignment_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Enqueue publishing all student submissions to GitHub."""
    from app.models.problem_set import ClassroomAssignment

    user_id = _get_current_user_id(request)
    now = datetime.now(timezone.utc)

    assignment_result = await db.execute(
        select(ClassroomAssignment).where(ClassroomAssignment.id == assignment_id)
    )
    assignment = assignment_result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if assignment.due_at and now < assignment.due_at:
        raise HTTPException(status_code=403, detail="Cannot publish before assignment due date")

    integration_result = await db.execute(
        select(GitHubIntegration).where(GitHubIntegration.teacher_id == user_id)
    )
    integration = integration_result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=400, detail="GitHub not connected. Connect GitHub first.")

    publish = GitHubPublish(
        assignment_id=assignment_id,
        initiated_by=user_id,
        status="pending",
    )
    db.add(publish)
    await db.commit()
    await db.refresh(publish)

    from workers.judge_task import publish_to_github
    publish_to_github.delay(str(publish.id))

    return {"publish_id": str(publish.id), "status": "pending"}


@router.get("/assignments/{assignment_id}/publish/status")
async def get_publish_status(
    assignment_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy.orm import selectinload

    _get_current_user_id(request)
    result = await db.execute(
        select(GitHubPublish)
        .options(selectinload(GitHubPublish.student_results))
        .where(GitHubPublish.assignment_id == assignment_id)
        .order_by(GitHubPublish.created_at.desc())
        .limit(1)
    )
    publish = result.scalar_one_or_none()
    if not publish:
        raise HTTPException(status_code=404, detail="No publish found for this assignment")

    return {
        "id": str(publish.id),
        "assignment_id": str(publish.assignment_id),
        "status": publish.status,
        "repo_url": publish.repo_url,
        "started_at": publish.started_at.isoformat() if publish.started_at else None,
        "completed_at": publish.completed_at.isoformat() if publish.completed_at else None,
        "created_at": publish.created_at.isoformat(),
        "student_results": [
            {
                "student_id": str(sr.student_id),
                "status": sr.status,
                "branch_name": sr.branch_name,
                "branch_url": sr.branch_url,
                "commits_pushed": sr.commits_pushed,
                "error_message": sr.error_message,
            }
            for sr in publish.student_results
        ],
    }


@router.post("/assignments/{assignment_id}/publish/retry", status_code=202)
async def retry_publish(
    assignment_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    from app.models.problem_set import ClassroomAssignment
    from sqlalchemy.orm import selectinload

    user_id = _get_current_user_id(request)

    assignment_result = await db.execute(
        select(ClassroomAssignment).where(ClassroomAssignment.id == assignment_id)
    )
    assignment = assignment_result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    integration_result = await db.execute(
        select(GitHubIntegration).where(GitHubIntegration.teacher_id == user_id)
    )
    integration = integration_result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=400, detail="GitHub not connected")

    publish = GitHubPublish(
        assignment_id=assignment_id,
        initiated_by=user_id,
        status="pending",
    )
    db.add(publish)
    await db.commit()
    await db.refresh(publish)

    from workers.judge_task import publish_to_github
    publish_to_github.delay(str(publish.id))

    return {"publish_id": str(publish.id), "status": "pending"}
