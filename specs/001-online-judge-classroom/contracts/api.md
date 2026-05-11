# API Contracts: Online Judge

**Date**: 2026-05-11
**Base URL**: `/api/v1`
**Auth**: 모든 엔드포인트는 세션 쿠키 인증 필요 (공개 엔드포인트 제외)

---

## 인증

### `GET /auth/google` — Google OAuth 시작
리디렉션: Google OAuth 동의 화면

### `GET /auth/google/callback` — OAuth 콜백
성공 시 세션 발급 후 프론트엔드로 리디렉션.

### `POST /auth/logout` — 로그아웃
세션 삭제.

### `GET /auth/me` — 현재 사용자 조회
```json
{
  "id": "uuid",
  "email": "string",
  "name": "string",
  "profile_picture_url": "string|null"
}
```

---

## 수업 & 과제

### `GET /courses` — 내 수업 목록
Classroom API에서 동기화 후 반환. 교사/학생 모두 사용.
```json
[{ "id": "uuid", "classroom_course_id": "string", "name": "string", "role": "teacher|student" }]
```

### `GET /courses/{course_id}/assignments` — 수업 내 과제 목록
```json
[{
  "id": "uuid",
  "title": "string",
  "scheduled_open_at": "ISO8601|null",
  "due_at": "ISO8601|null",
  "max_points": "number|null",
  "problem_set_id": "uuid|null",
  "is_linked": "boolean"
}]
```

### `POST /courses/{course_id}/assignments/{assignment_id}/sync` — 과제 일정 즉시 동기화 (교사)
Classroom API에서 최신 일정 가져와 DB 갱신. 응답: 갱신된 assignment 객체.

---

## 문제 세트 관리 (교사)

### `POST /problem-sets` — 문제 세트 생성
```json
// Request
{ "name": "string", "course_id": "uuid" }

// Response 201
{ "id": "uuid", "name": "string", "course_id": "uuid", "problems": [] }
```

### `PUT /problem-sets/{set_id}/link` — Classroom 과제에 연동
```json
// Request
{ "assignment_id": "uuid" }

// Response 200
{ "problem_set_id": "uuid", "assignment_id": "uuid" }
```

### `POST /problem-sets/{set_id}/problems` — 문제 추가
```json
// Request
{
  "title": "string",
  "description_md": "string",
  "input_description_md": "string|null",
  "output_description_md": "string|null",
  "time_limit_sec": "number",
  "memory_limit_mb": "integer",
  "max_points": "number",
  "allowed_languages": ["python3","java17","cpp17","c17"],
  "score_tiers": [
    { "min_attempts": 1, "max_attempts": 5, "score_ratio": 100.0 },
    { "min_attempts": 6, "max_attempts": 10, "score_ratio": 80.0 },
    { "min_attempts": 11, "max_attempts": null, "score_ratio": 60.0 }
  ]
}

// Response 201: Problem 객체 (test_cases 제외)
```

**Validation**:
- `score_tiers` 구간 겹침 시 → `400 Bad Request`
- `max_points` <= 0 → `400 Bad Request`
- `allowed_languages` 빈 배열 → `400 Bad Request`

### `PUT /problems/{problem_id}` — 문제 수정
Request: 문제 생성과 동일 구조 + `retroactive_score_update: boolean` (점수 구간 소급 적용 여부).

### `PATCH /problem-sets/{set_id}/problems/order` — 문제 순서 변경
```json
// Request
{ "problem_ids": ["uuid1", "uuid2", "uuid3"] }
```

### `POST /problems/{problem_id}/test-cases` — 테스트 케이스 업로드
`multipart/form-data`: `input_file`, `expected_output_file`, `is_public: boolean`.
```json
// Response 201
{ "id": "uuid", "order": "integer", "is_public": "boolean" }
```

---

## 학생 — 문제 세트 접근

### `GET /assignments/{assignment_id}/problem-set` — 문제 세트 조회
과제 공개 시각 이전이면 `403 Forbidden`. 마감 후이고 지각 미허용이면 `403 Forbidden`.

```json
{
  "problem_set": {
    "id": "uuid",
    "name": "string",
    "scheduled_open_at": "ISO8601|null",
    "due_at": "ISO8601|null",
    "allow_late_submission": "boolean"
  },
  "problems": [{
    "id": "uuid",
    "display_order": "integer",
    "title": "string",
    "description_md": "string",
    "time_limit_sec": "number",
    "memory_limit_mb": "integer",
    "max_points": "number",
    "allowed_languages": ["string"],
    "score_tiers": [{ "min_attempts": 1, "max_attempts": 5, "score_ratio": 100.0 }],
    "my_progress": {
      "attempt_count": "integer",
      "final_score": "number|null",
      "accepted": "boolean",
      "current_tier": { "score_ratio": "number" } | null,
      "next_tier": { "min_attempts": "integer", "score_ratio": "number" } | null
    },
    "public_test_cases": [{
      "order": "integer",
      "input_preview": "string",
      "expected_output_preview": "string"
    }]
  }],
  "my_total_score": "number",
  "is_late_access": "boolean"
}
```

---

## 코드 제출 & 채점

### `POST /problems/{problem_id}/submissions` — 코드 제출
```json
// Request
{ "code": "string", "language": "python3|java17|cpp17|c17" }

// Response 202 (채점 비동기 시작)
{ "submission_id": "uuid", "attempt_number": "integer", "status": "PENDING" }
```

**오류**:
- 미허용 언어 → `400`
- 과제 마감 & 지각 미허용 → `403`
- 코드 길이 0 → `400`

### `GET /submissions/{submission_id}` — 채점 결과 조회
```json
{
  "id": "uuid",
  "verdict": "PENDING|ACCEPTED|WRONG_ANSWER|...",
  "score": "number|null",
  "attempt_number": "integer",
  "is_late": "boolean",
  "test_case_results": [
    {
      "order": "integer",
      "verdict": "string",
      "time_ms": "integer",
      "memory_mb": "number",
      "input_preview": "string|null",
      "expected_output_preview": "string|null"
    }
  ],
  "judged_at": "ISO8601|null"
}
```

### `GET /submissions/{submission_id}/code` — 제출 코드 조회 (본인 또는 교사)
```json
{ "code": "string", "language": "string" }
```

### `GET /problems/{problem_id}/my-submissions` — 내 제출 이력
```json
[{
  "id": "uuid",
  "submitted_at": "ISO8601",
  "language": "string",
  "verdict": "string",
  "attempt_number": "integer",
  "score": "number|null",
  "is_late": "boolean"
}]
```

### `GET /submissions/{submission_id}/stream` — SSE 채점 결과 스트림
`Content-Type: text/event-stream`
```
event: verdict
data: {"verdict": "ACCEPTED", "score": 80.0, "attempt_number": 7}
```

---

## 교사 통계

### `GET /problem-sets/{set_id}/stats` — 문제 세트 통계
```json
{
  "total_students": "integer",
  "submitted_students": "integer",
  "avg_total_score": "number",
  "problems": [{
    "problem_id": "uuid",
    "title": "string",
    "submitted_count": "integer",
    "accepted_count": "integer",
    "avg_attempts": "number",
    "avg_score": "number"
  }]
}
```

### `GET /problem-sets/{set_id}/students/{student_id}/submissions` — 특정 학생 제출 이력 (교사)
제출 이력 목록 + 코드 접근 가능.

---

## GitHub 연동 & Publish

### `POST /github/connect` — 교사 GitHub OAuth 연동
GitHub OAuth 흐름 시작. 완료 후 `GitHubIntegration` 레코드 생성.
```json
// Response 200
{ "github_username": "string", "target_repo_name": "string" }
```

### `GET /github/status` — GitHub 연동 상태 조회 (교사)
```json
{ "connected": true, "github_username": "string", "target_repo_name": "string" }
```

### `POST /assignments/{assignment_id}/publish` — GitHub Publish 실행 (교사)
과제 마감 후에만 허용. 비동기 처리.
```json
// Response 202
{ "publish_id": "uuid", "status": "pending" }
```

**오류**: 마감 전 실행 → `403`. GitHub 미연동 → `400`.

### `GET /assignments/{assignment_id}/publish/status` — Publish 진행 상태 조회 (교사)
```json
{
  "publish_id": "uuid",
  "status": "running",
  "repo_url": "string|null",
  "total_students": 50,
  "completed_students": 23,
  "failed_students": 1,
  "student_results": [{
    "student_id": "uuid",
    "name": "string",
    "status": "success|failed|pending",
    "branch_url": "string|null",
    "commits_pushed": 8,
    "error_message": "string|null"
  }]
}
```

### `POST /assignments/{assignment_id}/publish/retry` — 실패 학생 재시도 (교사)
```json
// Request
{ "student_ids": ["uuid1", "uuid2"] }
// Response 202
{ "publish_id": "uuid", "retrying_count": 2 }
```

---

## 제출 기록 & 코드 유사도 분석

### `GET /courses/{course_id}/dashboard` — 교사 수업 대시보드
교사가 접근 가능한 수업 목록과 각 수업의 과제 현황 요약.
```json
[{
  "course_id": "uuid",
  "name": "string",
  "assignments": [{
    "assignment_id": "uuid",
    "title": "string",
    "due_at": "ISO8601|null",
    "submitted_count": "integer",
    "total_students": "integer"
  }]
}]
```

### `GET /assignments/{assignment_id}/students` — 과제 학생 목록 + 현황 (교사)
```json
[{
  "student_id": "uuid",
  "name": "string",
  "email": "string",
  "total_score": "number",
  "problems": [{
    "problem_id": "uuid",
    "attempt_count": "integer",
    "final_score": "number",
    "accepted": "boolean"
  }]
}]
```

### `GET /assignments/{assignment_id}/students/{student_id}/history` — 학생 전체 제출 이력 (교사)
문제별로 그룹화된 전체 제출 이력. 코드 포함.
```json
[{
  "problem_id": "uuid",
  "title": "string",
  "submissions": [{
    "id": "uuid",
    "attempt_number": "integer",
    "submitted_at": "ISO8601",
    "language": "string",
    "verdict": "string",
    "score": "number|null",
    "code": "string",
    "is_late": "boolean"
  }]
}]
```

### `POST /assignments/{assignment_id}/similarity-analysis` — 유사도 분석 실행 (교사)
과제 마감 후에만 실행 가능. 비동기 처리.
```json
// Request
{ "threshold": 80.0 }  // 기본값 80, 선택사항

// Response 202
{ "task_id": "uuid", "status": "running", "estimated_minutes": 5 }
```

### `GET /assignments/{assignment_id}/similarity-reports` — 유사도 분석 결과 조회 (교사)
```json
{
  "analyzed_at": "ISO8601",
  "threshold": 80.0,
  "problems": [{
    "problem_id": "uuid",
    "title": "string",
    "flagged_pairs": [{
      "student_a": { "id": "uuid", "name": "string" },
      "student_b": { "id": "uuid", "name": "string" },
      "similarity_score": 92.5,
      "submission_a_id": "uuid",
      "submission_b_id": "uuid"
    }],
    "total_pairs_analyzed": "integer"
  }]
}
```

### `GET /similarity-reports/{report_id}/diff` — 두 제출 코드 나란히 비교 (교사)
```json
{
  "student_a": { "id": "uuid", "name": "string", "code": "string", "language": "string" },
  "student_b": { "id": "uuid", "name": "string", "code": "string", "language": "string" },
  "similarity_score": 92.5
}
```

---

## 에러 응답 공통 형식

```json
{
  "error": {
    "code": "VALIDATION_ERROR|FORBIDDEN|NOT_FOUND|...",
    "message": "string",
    "details": {} | null
  }
}
```
