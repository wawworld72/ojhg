# Tasks: Google Classroom-Integrated Online Judge

**Input**: Design documents from `/specs/001-online-judge-classroom/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/api.md ✅, contracts/sandbox.md ✅

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4 + USP for Publish, USS for Similarity, USI for JSON Import)
- Include exact file paths in descriptions

## Path Conventions (per plan.md)

```
backend/app/          — FastAPI 애플리케이션
backend/judge/        — 샌드박스 실행
backend/workers/      — Celery 태스크
backend/alembic/      — DB 마이그레이션
frontend/src/app/     — Next.js App Router 페이지
frontend/src/components/ — React 컴포넌트
infra/                — Docker Compose, Nginx
```

---

## Phase 1: Setup (공유 인프라 초기화)

**Purpose**: 모노레포 구조 생성 및 개발 환경 구성

- [ ] T001 Create monorepo directory structure (backend/, frontend/, judge/, infra/, .github/) per plan.md project structure
- [ ] T002 Initialize Python backend with pyproject.toml (FastAPI, SQLAlchemy 2, Celery, google-auth-oauthlib, alembic, pydantic, pytest, pytest-asyncio)
- [ ] T003 [P] Initialize Next.js 14 frontend with TypeScript, React 18, Monaco Editor in frontend/package.json
- [ ] T004 [P] Create infra/docker-compose.yml with postgres:16, redis:7, backend, celery-worker, frontend, nginx services
- [ ] T005 [P] Create judge/images/ Dockerfiles for python3 (python:3.12-slim), java17 (openjdk:17-slim), cpp17 (gcc:13-slim), c17 (gcc:13-slim) with uid=1001 non-root user
- [ ] T006 [P] Create .github/workflows/ci.yml running pytest (backend) and Jest (frontend) on pull requests
- [ ] T007 Create infra/.env.example with DATABASE_URL, REDIS_URL, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, SECRET_KEY, ENCRYPTION_KEY, GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET

---

## Phase 2: Foundational (모든 User Story의 선행 전제)

**Purpose**: 인증·DB·비동기 인프라 — 이 Phase 완료 전까지 어떤 User Story도 시작 불가

**⚠️ CRITICAL**: 모든 User Story는 이 Phase 완료 후에만 진행 가능

- [ ] T008 Implement backend/app/core/config.py (Pydantic Settings, env var loading for DB/Redis/Google OAuth/GitHub/Encryption)
- [ ] T009 Implement backend/app/core/database.py (SQLAlchemy 2 async engine, AsyncSession factory, get_db dependency)
- [ ] T010 Implement backend/app/core/security.py (AES-256 token encryption/decryption, session token generation)
- [ ] T011 [P] Create SQLAlchemy ORM model backend/app/models/user.py (User, fields: id/google_id/email/name/profile_picture_url/encrypted_refresh_token)
- [ ] T012 [P] Create SQLAlchemy ORM model backend/app/models/course.py (Course, CourseEnrollment with role ENUM teacher/student)
- [ ] T013 [P] Create SQLAlchemy ORM model backend/app/models/problem_set.py (ProblemSet, ClassroomAssignment, StudentAssignmentExtension)
- [ ] T014 [P] Create SQLAlchemy ORM model backend/app/models/problem.py (Problem, AttemptScoreTier, TestCase)
- [ ] T015 [P] Create SQLAlchemy ORM model backend/app/models/submission.py (Submission with verdict ENUM, test_case_results JSONB; StudentProblemProgress)
- [ ] T016 [P] Create SQLAlchemy ORM model backend/app/models/grade_passback.py (GradePassbackLog with status ENUM pending/success/failed)
- [ ] T017 [P] Create SQLAlchemy ORM model backend/app/models/github.py (GitHubIntegration, GitHubPublish, GitHubPublishStudentResult)
- [ ] T018 [P] Create SQLAlchemy ORM model backend/app/models/similarity.py (SimilarityReport with UNIQUE(assignment_id, problem_id, student_a_id, student_b_id))
- [ ] T019 Initialize Alembic in backend/alembic/ and generate initial migration from all models (T011–T018)
- [ ] T020 Configure Celery app in backend/workers/celery_app.py (Redis broker/backend, task autodiscovery, retry policy defaults)
- [ ] T021 Implement backend/app/main.py (FastAPI app, CORS, session middleware, error handler for common error codes, include all API routers)
- [ ] T022 [P] Implement frontend/src/services/api.ts (Axios/fetch client with session cookie, error interceptor, typed response helpers)

**Checkpoint**: DB 마이그레이션 적용 가능, Celery worker 기동 가능, FastAPI 앱 기동 가능 — User Story 구현 시작 가능

---

## Phase 3: User Story 1 — 학생: 문제 세트 접근 및 코드 제출 (Priority: P1) 🎯 MVP

**Goal**: 학생이 Google Classroom 과제 링크로 진입해 문제 세트를 보고, 코드를 제출하여 채점 결과와 획득 점수를 확인한다.

**Independent Test**: 학생 계정으로 Classroom 과제 클릭 → 문제 세트 페이지 진입 → 문제 1 코드 제출 → 채점 결과 + 시도 횟수 + 획득 점수 확인.

### Implementation for User Story 1

- [ ] T023 [US1] Implement Google OAuth2 auth flow in backend/app/api/v1/auth.py (GET /auth/google → redirect, GET /auth/google/callback → session, POST /auth/logout, GET /auth/me) using google-auth-oauthlib with scopes from research.md
- [ ] T024 [US1] Implement backend/app/services/classroom_api.py Google Classroom API client (courses.courseWork.get for assignment sync, courses.students.list for enrollment check, token refresh via encrypted_refresh_token)
- [ ] T025 [P] [US1] Create Pydantic schemas backend/app/schemas/submission.py (SubmissionCreate, SubmissionResponse, TestCaseResult, SubmissionListItem)
- [ ] T026 [P] [US1] Create Pydantic schemas backend/app/schemas/problem.py (ProblemResponse, ScoreTierResponse, MyProgressResponse, PublicTestCaseResponse, ProblemSetDetailResponse)
- [ ] T027 [US1] Implement GET /assignments/{assignment_id}/problem-set in backend/app/api/v1/problem_sets.py (access control: 403 if before scheduled_open_at or after due_at with allow_late_submission=false; compute my_progress per problem using StudentProblemProgress; return public test cases preview)
- [ ] T028 [US1] Implement backend/app/services/scoring.py (find_score_tier(attempt_count, tiers) → score_ratio; compute final_score = max_points × score_ratio / 100)
- [ ] T029 [US1] Implement POST /problems/{problem_id}/submissions in backend/app/api/v1/submissions.py (validate language/deadline; SELECT FOR UPDATE on StudentProblemProgress to atomically increment attempt_count; create Submission with PENDING verdict; enqueue judge_task; return 202 with submission_id and attempt_number)
- [ ] T030 [US1] Implement judge/sandbox.py Docker sandbox runner (docker run --network none --read-only --tmpfs /tmp:size=32m --cpus 1 --memory <limit>m --pids-limit 64 --user 1001; execute per language command from sandbox.md; capture stdout/stderr; enforce time_limit_sec via timeout + docker stop)
- [ ] T031 [US1] Implement judge/compare.py output comparison (strip trailing whitespace per line, normalize line endings, byte-compare; return ACCEPTED or WRONG_ANSWER)
- [ ] T032 [US1] Implement backend/workers/judge_task.py Celery task (fetch submission+test cases; call sandbox per test case; aggregate overall_verdict per priority in sandbox.md; update Submission.verdict/test_case_results/score/judged_at; update StudentProblemProgress.final_score and first_accepted_attempt if first Accepted; enqueue grade passback task)
- [ ] T033 [US1] Implement GET /submissions/{submission_id} in backend/app/api/v1/submissions.py (return verdict, score, test_case_results with public/non-public input preview)
- [ ] T034 [US1] Implement GET /submissions/{submission_id}/stream SSE endpoint in backend/app/api/v1/submissions.py (poll DB every 1s until judged_at set, emit verdict event, close stream)
- [ ] T035 [US1] Implement GET /problems/{problem_id}/my-submissions in backend/app/api/v1/submissions.py (list student's submissions ordered by submitted_at DESC)
- [ ] T036 [P] [US1] Create Next.js problem set page frontend/src/app/assignments/[id]/page.tsx (fetch problem set, list problems with attempt_count/final_score/score_tier display, navigate to individual problem)
- [ ] T037 [P] [US1] Create Monaco Editor submission component frontend/src/components/editor/ (language selector, file upload support for .py/.java/.cpp/.c, submit button, attempt count + next tier display)
- [ ] T038 [US1] Create judge result display component frontend/src/components/judge/ (SSE-based real-time update, per-test-case verdict table, overall verdict badge, score gained display)

**Checkpoint**: 학생이 Classroom 링크 → 문제 세트 → 코드 제출 → 채점 결과 확인 흐름이 end-to-end 동작

---

## Phase 4: User Story 2 — 교사: 문제 세트 구성 및 Classroom 연동 (Priority: P1)

**Goal**: 교사가 문제 세트를 생성하고 문제(테스트 케이스, 점수 구간 포함)를 추가한 뒤 Classroom 과제에 연동한다. Classroom 일정이 온라인 저지에 자동 동기화된다.

**Independent Test**: 교사가 2개 문제 포함 문제 세트 생성 → Classroom 과제 연동 → 학생 계정으로 해당 과제 접근 확인.

### Implementation for User Story 2

- [ ] T039 [P] [US2] Create Pydantic schemas backend/app/schemas/problem_set.py (ProblemSetCreate, ProblemSetResponse, LinkAssignmentRequest, ProblemOrderRequest)
- [ ] T040 [P] [US2] Create Pydantic schemas backend/app/schemas/course.py (CourseResponse, AssignmentResponse, CourseSyncResponse)
- [ ] T041 [US2] Implement GET /courses and GET /courses/{course_id}/assignments in backend/app/api/v1/courses.py (call classroom_api.py to sync courses/assignments on request; upsert Course, ClassroomAssignment, CourseEnrollment in DB; return role-aware response)
- [ ] T042 [US2] Implement POST /courses/{course_id}/assignments/{assignment_id}/sync in backend/app/api/v1/courses.py (on-demand sync of scheduled_open_at/due_at/max_points from Classroom API; teacher-only)
- [ ] T043 [US2] Implement POST /problem-sets and GET /problem-sets/{set_id} in backend/app/api/v1/problem_sets.py (teacher creates problem set linked to course; return shareable link)
- [ ] T044 [US2] Implement PUT /problem-sets/{set_id}/link in backend/app/api/v1/problem_sets.py (link problem set to ClassroomAssignment; enforce 1:1 uniqueness; sync schedule from Classroom immediately)
- [ ] T045 [US2] Implement POST /problem-sets/{set_id}/problems in backend/app/api/v1/problems.py (validate score_tiers for overlap using service; auto-assign display_order; validate time_limit_sec 0.5–10.0, memory_limit_mb 32–512)
- [ ] T046 [US2] Implement PUT /problems/{problem_id} in backend/app/api/v1/problems.py (update problem fields; handle retroactive_score_update flag to recalculate final_score for existing accepted submissions)
- [ ] T047 [US2] Implement PATCH /problem-sets/{set_id}/problems/order in backend/app/api/v1/problem_sets.py (reorder problems by provided problem_ids list; update display_order atomically)
- [ ] T048 [US2] Implement POST /problems/{problem_id}/test-cases in backend/app/api/v1/problems.py (accept multipart/form-data input_file + expected_output_file + is_public; store files to local volume with storage_key; enforce max 100 per problem)
- [ ] T049 [US2] Implement Celery beat periodic task in backend/workers/grade_sync_task.py for 15-minute Classroom schedule polling (fetch all linked ClassroomAssignments; sync scheduled_open_at/due_at/max_points; update StudentAssignmentExtension per student extension)
- [ ] T050 [P] [US2] Create teacher problem set management pages frontend/src/app/teacher/problem-sets/ (create/edit problem set, problem list with drag-and-drop reorder, link to Classroom assignment selector)
- [ ] T051 [P] [US2] Create problem editor component frontend/src/components/problem/ (Markdown description editor, test case upload, score tier table editor with overlap validation feedback, allowed language checkboxes)

**Checkpoint**: 교사가 문제 세트 생성 → 문제 추가 → Classroom 연동 → 학생 접근 가능 상태

---

## Phase 5: User Story 3 — Google Classroom 최종 성적 자동 반영 (Priority: P1)

**Goal**: 학생의 채점 완료 후 5분 이내, 과제 마감 시 일괄 확정으로 Classroom 성적부가 자동 갱신된다.

**Independent Test**: 학생이 문제 세트 내 모든 문제 제출 → 각 문제 점수 합산 → Google Classroom 성적부에서 최종 점수 확인 (5분 이내).

### Implementation for User Story 3

- [ ] T052 [P] [US3] Create Pydantic schemas backend/app/schemas/grade_passback.py (GradePassbackRequest, GradePassbackStatus)
- [ ] T053 [US3] Implement backend/app/services/grade_passback.py (calculate student's total score across all problems in assignment; call courses.courseWork.studentSubmissions.patch + return via Classroom API; idempotent: skip if score unchanged; store GradePassbackLog; retry up to 3 times with exponential backoff)
- [ ] T054 [US3] Implement Celery task backend/workers/grade_sync_task.py grade_passback_task (triggered by judge_task on completion; call grade_passback service; on failure after 3 retries, mark GradePassbackLog.status=failed and send teacher notification)
- [ ] T055 [US3] Implement deadline batch finalization in backend/workers/grade_sync_task.py (Celery beat checks every minute for assignments whose due_at just passed; for each enrolled student compute final total; passback to Classroom; mark problem set finalized)
- [ ] T056 [US3] Implement teacher failure notification mechanism in backend/app/services/grade_passback.py (on repeated passback failure, expose alert via GET /assignments/{assignment_id}/passback-failures endpoint for teacher dashboard polling)

**Checkpoint**: 채점 → 성적 반영이 5분 이내 자동화, 마감 일괄 확정 동작, 실패 알림 노출

---

## Phase 6: User Story 4 — 교사 과제 현황 모니터링 (Priority: P2)

**Goal**: 교사가 수업→과제→학생 계층으로 제출 현황을 탐색하고 학생별 전체 제출 이력(코드 포함)을 조회한다.

**Independent Test**: 교사 대시보드 → 문제 세트 통계 페이지 → 문제별 학생 현황 확인 → 특정 학생 클릭 → 전체 제출 이력(코드 포함) 확인. 4번 이내 클릭.

### Implementation for User Story 4

- [ ] T057 [P] [US4] Create Pydantic schemas backend/app/schemas/stats.py (CourseDashboardResponse, AssignmentStudentListResponse, ProblemSetStatsResponse, StudentHistoryResponse)
- [ ] T058 [US4] Implement GET /courses/{course_id}/dashboard in backend/app/api/v1/courses.py (teacher dashboard: list courses with per-assignment submitted_count/total_students summary)
- [ ] T059 [US4] Implement GET /assignments/{assignment_id}/students in backend/app/api/v1/problem_sets.py (per-student total_score + per-problem attempt_count/final_score/accepted)
- [ ] T060 [US4] Implement GET /problem-sets/{set_id}/stats in backend/app/api/v1/problem_sets.py (aggregate submitted_count, accepted_count, avg_attempts, avg_score per problem)
- [ ] T061 [US4] Implement GET /assignments/{assignment_id}/students/{student_id}/history in backend/app/api/v1/submissions.py (all submissions grouped by problem, ordered by attempt_number; include code field)
- [ ] T062 [US4] Implement GET /submissions/{submission_id}/code in backend/app/api/v1/submissions.py (allow student (own) or teacher access; return code + language)
- [ ] T063 [P] [US4] Create teacher stats dashboard page frontend/src/app/teacher/stats/[setId]/page.tsx (problem-level stats table: submitted_count, accepted_count, avg_attempts, avg_score)
- [ ] T064 [P] [US4] Create student submission history component frontend/src/components/ (per-problem submission list with code viewer modal, verdict badge, score, is_late flag)

**Checkpoint**: 교사가 수업→과제→학생→제출 이력 4 클릭 탐색 동작

---

## Phase 7: GitHub Publish (과제 마감 후 학생 코드 브랜치 업로드)

**Goal**: 교사가 GitHub OAuth 연동 후 Publish를 실행하면 학생×문제 단위 브랜치로 전체 제출 이력이 git push 프로토콜로 업로드된다.

**Independent Test**: 교사 GitHub 연동 → 마감된 과제 Publish → 50명 × 5문제 브랜치 생성 + 커밋 이력 확인 → 10분 이내 완료.

### Implementation for GitHub Publish

- [ ] T065 [P] [USP] Create Pydantic schemas backend/app/schemas/github_publish.py (GitHubConnectResponse, PublishRequest, PublishStatusResponse, StudentPublishResult)
- [ ] T066 [USP] Implement GitHub OAuth connect flow in backend/app/api/v1/github.py (POST /github/connect: redirect to GitHub OAuth; callback: exchange code, store encrypted token in GitHubIntegration; GET /github/status)
- [ ] T067 [USP] Implement backend/app/services/github_publish.py git-push uploader (use subprocess git or PyGit2; for each student×problem branch: clone/init bare repo locally, create branch submissions/{assignment-slug}/{problem-slug}/{student-slug}, commit each submission in attempt_number order with message format "[Attempt #N] {verdict} — {ISO8601}\nScore: {score} | Language: {lang}"; git push to GitHub via HTTPS with teacher token; auto-create private repo if missing via GitHub REST API POST /user/repos)
- [ ] T068 [USP] Implement POST /assignments/{assignment_id}/publish in backend/app/api/v1/github.py (403 if before due_at; 400 if GitHubIntegration missing; create GitHubPublish record; enqueue publish_task; return 202 with publish_id)
- [ ] T069 [USP] Implement GET /assignments/{assignment_id}/publish/status and POST /assignments/{assignment_id}/publish/retry in backend/app/api/v1/github.py
- [ ] T070 [USP] Implement backend/workers/judge_task.py publish_task Celery task (process students in parallel batches; call github_publish.py per student; update GitHubPublishStudentResult status/branch_url/commits_pushed; update GitHubPublish.status to completed/partial/failed)
- [ ] T071 [P] [USP] Create teacher Publish UI frontend/src/app/teacher/ (GitHub connect button; Publish button (disabled before due_at); real-time status with progress bar: N/50 students completed; failed student list with retry button; repo + branch URLs)

**Checkpoint**: Publish 완료 후 GitHub에서 git log로 학생별 제출 이력 확인 가능

---

## Phase 8: 코드 유사도 분석 (부정행위 탐지)

**Goal**: 교사가 마감 후 유사도 분석을 실행하면 학생 쌍별 유사도 점수와 코드 나란히 비교가 가능하다.

**Independent Test**: 교사 → POST /similarity-analysis → 수강생 50명 기준 10분 이내 결과 → 주의 요망(≥80%) 쌍 확인 → 코드 diff 뷰어 동작.

### Implementation for Similarity Analysis

- [ ] T072 [P] [USS] Create Pydantic schemas backend/app/schemas/similarity.py (SimilarityAnalysisRequest, SimilarityReportResponse, SimilarityPairDetail, CodeDiffResponse)
- [ ] T073 [USS] Implement backend/app/services/similarity.py token-based similarity analyzer (language-aware tokenizer per python3/java17/cpp17/c17; normalize variable names and string literals; compute Jaccard similarity on token n-gram sets; return 0.0–100.0 score)
- [ ] T074 [USS] Implement POST /assignments/{assignment_id}/similarity-analysis in backend/app/api/v1/similarity.py (403 if before due_at; accept optional threshold (default 80.0); enqueue async task; return 202 with task_id)
- [ ] T075 [USS] Implement Celery task for similarity analysis (fetch all submissions per problem; compute all student pairs N×(N-1)/2; store results in SimilarityReport with is_flagged=true if score ≥ threshold; upsert existing records on re-run)
- [ ] T076 [USS] Implement GET /assignments/{assignment_id}/similarity-reports in backend/app/api/v1/similarity.py (return per-problem flagged pairs sorted by similarity_score DESC)
- [ ] T077 [USS] Implement GET /similarity-reports/{report_id}/diff in backend/app/api/v1/similarity.py (return both students' code + language + similarity_score)
- [ ] T078 [P] [USS] Create frontend similarity analysis UI (run analysis button; per-problem flagged pairs table with similarity_score; click pair → side-by-side code diff viewer with syntax highlight)

**Checkpoint**: 50명 과제 유사도 분석 10분 이내, 주의 요망 쌍 코드 비교 가능

---

## Phase 9: JSON 임포트 (문제/과제 파일 일괄 구성)

**Goal**: 교사가 problem.schema.json 또는 assignment.schema.json 파일을 업로드하면 문제/문제 세트가 자동 구성된다.

**Independent Test**: 교사가 문제 정의 JSON 업로드 → 유효성 검사 에러 표시 → 수정 후 재업로드 → 문제 세트 자동 생성 확인.

### Implementation for JSON Import

- [ ] T079 [P] [USI] Define problem.schema.json (title, description_md, time_limit_sec, memory_limit_mb, max_points, allowed_languages, score_tiers, test_cases[{input, expected_output, is_sample}], display_id) in specs/001-online-judge-classroom/problem-schema/
- [ ] T080 [P] [USI] Define assignment.schema.json (name, problems[{ref: path|inline problem definition}]) in specs/001-online-judge-classroom/problem-schema/
- [ ] T081 [USI] Implement backend/app/services/json_import.py (validate JSON against schema using jsonschema library; check score_tier overlap; collect all violations into list; on display_id conflict, return conflict list for teacher decision)
- [ ] T082 [USI] Implement POST /problems/import (multipart JSON upload) in backend/app/api/v1/problems.py (run validation; on errors return 422 with per-field violations; on success create Problem + AttemptScoreTier + TestCase records; handle is_sample → is_public mapping)
- [ ] T083 [USI] Implement POST /problem-sets/import (assignment.schema.json upload) in backend/app/api/v1/problem_sets.py (resolve ref paths or inline; create ProblemSet + Problems in one transaction; return conflicts for teacher overwrite/cancel choice)
- [ ] T084 [P] [USI] Create frontend JSON import UI (file dropzone; validation error list with field paths; conflict resolution dialog for duplicate display_id; success summary with created problem count)

**Checkpoint**: JSON 업로드 → 유효성 검사 → 문제 세트 자동 생성 동작

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: 다수 User Story에 걸친 품질 개선 및 운영 준비

- [ ] T085 [P] Add comprehensive structured logging (request ID, user ID, submission ID) across all API endpoints using Python logging + middleware in backend/app/main.py
- [ ] T086 [P] Verify all DB indexes from data-model.md are present in Alembic migrations (Submission composite index, GradePassbackLog status index, SimilarityReport flagged index)
- [ ] T087 Configure SQLAlchemy async connection pool (pool_size=10, max_overflow=20) and Celery concurrency=8 workers in infra/docker-compose.yml
- [ ] T088 [P] Create infra/docker-compose.prod.yml for Hetzner CX42 VPS deployment (same services, production env, restart: always)
- [ ] T089 [P] Configure infra/nginx/nginx.conf (SSL termination via Cloudflare, reverse proxy to backend:8000 and frontend:3000, /api/ routing)
- [ ] T090 Run quickstart.md validation scenarios (teacher creates problem set, student submits, grade reflects in Classroom) and fix any gaps
- [ ] T091 [P] Security hardening: verify AES-256 encryption of tokens (security.py), confirm sandbox --network none enforced, check SQL injection via ORM parameterization
- [ ] T092 Implement edge case handlers: duplicate submission race condition guard (SELECT FOR UPDATE verified), Classroom assignment deleted notification, pre-due_at publish block with clear error

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 즉시 시작 가능
- **Foundational (Phase 2)**: Phase 1 완료 후 — **모든 User Story를 블로킹**
- **US1 (Phase 3)**: Phase 2 완료 후 — 다른 Story에 독립적 (MVP 배포 지점)
- **US2 (Phase 4)**: Phase 2 완료 후 — US1과 병행 가능 (US1이 있어야 학생 테스트 가능)
- **US3 (Phase 5)**: Phase 3 + Phase 4 완료 후 (채점 + Classroom 연동 필요)
- **US4 (Phase 6)**: Phase 3 + Phase 4 완료 후 — US3와 병행 가능
- **GitHub Publish (Phase 7)**: Phase 3 완료 후 (제출 데이터 필요)
- **Similarity (Phase 8)**: Phase 3 완료 후 — Phase 7과 병행 가능
- **JSON Import (Phase 9)**: Phase 4 완료 후 — Phase 7, 8과 병행 가능
- **Polish (Phase 10)**: 원하는 Phase 완료 후

### User Story Dependencies

- **US1 (P1)**: Phase 2 이후 독립 시작 — **MVP 최소 단위**
- **US2 (P1)**: Phase 2 이후 독립 시작 — US1과 병행 가능
- **US3 (P1)**: US1 + US2 완료 후 (채점 결과 + Classroom 연동 모두 필요)
- **US4 (P2)**: US1 + US2 완료 후 (제출 데이터 + 문제 세트 구조 필요)
- **USP (GitHub Publish)**: US1 완료 후 (제출 이력 필요)
- **USS (Similarity)**: US1 완료 후 (제출 이력 필요)
- **USI (JSON Import)**: US2 완료 후 (문제 생성 로직 재사용)

### Within Each User Story

- Pydantic 스키마([P]) → 서비스 → API 엔드포인트 → 프론트엔드 컴포넌트
- 모델은 Phase 2에서 선행 완료
- 각 Story는 독립적으로 테스트 가능한 Checkpoint에서 검증

---

## Parallel Example: User Story 1

```bash
# 병렬로 시작 가능 (다른 파일, 의존성 없음):
Task T025: backend/app/schemas/submission.py
Task T026: backend/app/schemas/problem.py
Task T036: frontend/src/app/assignments/[id]/page.tsx
Task T037: frontend/src/components/editor/

# T025, T026 완료 후 순차 진행:
Task T027: GET /assignments/{assignment_id}/problem-set 엔드포인트
Task T028: backend/app/services/scoring.py

# T030, T031 완료 후:
Task T032: backend/workers/judge_task.py (sandbox + compare 의존)
```

## Parallel Example: User Story 2

```bash
# 병렬로 시작 가능:
Task T039: backend/app/schemas/problem_set.py
Task T040: backend/app/schemas/course.py
Task T050: frontend/src/app/teacher/problem-sets/
Task T051: frontend/src/components/problem/

# T041 완료 후:
Task T042: on-demand sync 엔드포인트
Task T043: POST /problem-sets
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1: Setup 완료
2. Phase 2: Foundational 완료 (CRITICAL)
3. Phase 3: User Story 1 완료
4. **STOP and VALIDATE**: 학생 제출 → 채점 → 결과 확인 end-to-end 테스트
5. MVP 데모 가능

### Incremental Delivery

1. Setup + Foundational → 인프라 준비
2. US1 → **MVP**: 학생 제출/채점 동작 → 데모/검증
3. US2 → 교사가 직접 문제 세트 관리 가능
4. US3 → Classroom 성적 자동 반영 (핵심 가치 완성)
5. US4 → 모니터링 대시보드
6. USP → GitHub Publish (코드 이력 보존)
7. USS → 유사도 분석 (부정행위 탐지)
8. USI → JSON 임포트 (운영 편의)

### Parallel Team Strategy

Phase 2 완료 후 병행 가능:
- **Developer A**: US1 (Phase 3) — 채점 핵심
- **Developer B**: US2 (Phase 4) — 문제 세트 관리
- **Developer C**: 인프라/Docker 최적화

US1 + US2 완료 후:
- **Developer A**: US3 (성적 반영)
- **Developer B**: US4 (대시보드)

---

## Notes

- [P] 태스크 = 다른 파일, 완료된 태스크 미의존 → 병렬 실행 가능
- [USx] 레이블로 특정 User Story와 태스크 간 추적 가능
- 각 User Story는 Checkpoint에서 독립적으로 검증
- 커밋은 태스크 단위 또는 논리 그룹 단위로
- 모든 민감 정보(토큰, 키)는 security.py AES-256 암호화 필수
- 샌드박스 테스트는 실제 Docker 실행 환경(Docker Desktop)에서 수행
- plan.md의 Constitution Check 준수: TDD는 선택적(spec에 명시 시), 보안 격리는 필수
