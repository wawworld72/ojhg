import uuid
from datetime import datetime

from pydantic import BaseModel


class GitHubConnectResponse(BaseModel):
    github_username: str
    target_repo_name: str
    connected: bool


class PublishRequest(BaseModel):
    pass


class StudentPublishResult(BaseModel):
    student_id: uuid.UUID
    status: str
    branch_name: str | None = None
    branch_url: str | None = None
    commits_pushed: int
    error_message: str | None = None


class PublishStatusResponse(BaseModel):
    id: uuid.UUID
    assignment_id: uuid.UUID
    status: str
    repo_url: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    student_results: list[StudentPublishResult] = []

    model_config = {"from_attributes": True}
