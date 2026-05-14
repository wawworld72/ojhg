"""Google Classroom API client wrapper."""
from __future__ import annotations

import asyncio
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


class ClassroomAPIClient:
    def __init__(self, credentials: Credentials):
        self._creds = credentials

    def _service(self, name: str, version: str):
        return build(name, version, credentials=self._creds, cache_discovery=False)

    async def get_user_profile(self) -> dict[str, Any]:
        def _call():
            svc = self._service("oauth2", "v2")
            return svc.userinfo().get().execute()  # type: ignore[attr-defined]

        return await asyncio.get_event_loop().run_in_executor(None, _call)

    async def list_courses(self, teacher_id: str | None = None, student_id: str | None = None) -> list[dict[str, Any]]:
        def _call():
            svc = self._service("classroom", "v1")
            kwargs: dict = {"courseStates": ["ACTIVE"]}
            if teacher_id:
                kwargs["teacherId"] = teacher_id
            if student_id:
                kwargs["studentId"] = student_id
            result = svc.courses().list(**kwargs).execute()  # type: ignore
            return result.get("courses", [])

        return await asyncio.get_event_loop().run_in_executor(None, _call)

    async def list_coursework(self, course_id: str) -> list[dict[str, Any]]:
        def _call():
            svc = self._service("classroom", "v1")
            result = svc.courses().courseWork().list(courseId=course_id).execute()  # type: ignore
            return result.get("courseWork", [])

        return await asyncio.get_event_loop().run_in_executor(None, _call)

    async def get_coursework(self, course_id: str, coursework_id: str) -> dict[str, Any]:
        def _call():
            svc = self._service("classroom", "v1")
            return svc.courses().courseWork().get(  # type: ignore
                courseId=course_id, id=coursework_id
            ).execute()

        return await asyncio.get_event_loop().run_in_executor(None, _call)

    async def list_students(self, course_id: str) -> list[dict[str, Any]]:
        def _call():
            svc = self._service("classroom", "v1")
            result = svc.courses().students().list(courseId=course_id).execute()  # type: ignore
            return result.get("students", [])

        return await asyncio.get_event_loop().run_in_executor(None, _call)

    async def patch_grade(
        self, course_id: str, coursework_id: str, submission_id: str, score: float
    ) -> None:
        def _call():
            svc = self._service("classroom", "v1")
            svc.courses().courseWork().studentSubmissions().patch(  # type: ignore
                courseId=course_id,
                courseWorkId=coursework_id,
                id=submission_id,
                updateMask="assignedGrade,draftGrade",
                body={"assignedGrade": score, "draftGrade": score},
            ).execute()
            svc.courses().courseWork().studentSubmissions().return_(  # type: ignore
                courseId=course_id,
                courseWorkId=coursework_id,
                body={"ids": [submission_id]},
            ).execute()

        await asyncio.get_event_loop().run_in_executor(None, _call)

    async def list_student_submissions(
        self, course_id: str, coursework_id: str
    ) -> list[dict[str, Any]]:
        def _call():
            svc = self._service("classroom", "v1")
            result = (
                svc.courses()  # type: ignore
                .courseWork()
                .studentSubmissions()
                .list(courseId=course_id, courseWorkId=coursework_id)
                .execute()
            )
            return result.get("studentSubmissions", [])

        return await asyncio.get_event_loop().run_in_executor(None, _call)
