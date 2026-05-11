# Data Model: Google Classroom-Integrated Online Judge

**Date**: 2026-05-11
**Branch**: `claude/implement-spec-kit-3P5ga`

---

## Entity Relationship Overview

```
User ──────────────────────────────────────────────────────────┐
 │ (teacher)                                                    │ (student)
 ▼                                                             ▼
Course ────── ClassroomAssignment ──── ProblemSet ──── StudentProblemProgress
                     │                     │
                     │              Problem (ordered)
                     │               ├── AttemptScoreTier (1..N)
                     │               ├── TestCase (1..100)
                     │               └── Submission (via student)
                     │
                GradePassbackLog
```

---

## Entities

### User

| 필드 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | 내부 식별자 |
| google_id | VARCHAR(255) | UNIQUE NOT NULL | Google 계정 sub |
| email | VARCHAR(255) | UNIQUE NOT NULL | Google 이메일 |
| name | VARCHAR(255) | NOT NULL | 표시 이름 |
| profile_picture_url | TEXT | NULL | 구글 프로필 사진 |
| encrypted_refresh_token | TEXT | NULL | Google OAuth refresh token (AES-256 암호화) |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

**비즈니스 규칙**:
- 역할(교사/학생)은 User에 저장하지 않음 — Classroom 수업별 역할은 CourseEnrollment에서 관리.
- refresh_token은 백엔드에서만 접근 가능.

---

### Course

| 필드 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | |
| classroom_course_id | VARCHAR(255) | UNIQUE NOT NULL | Google Classroom course ID |
| name | VARCHAR(500) | NOT NULL | 수업명 |
| section | VARCHAR(255) | NULL | 섹션/분반 |
| synced_at | TIMESTAMPTZ | NULL | 마지막 Classroom 동기화 시각 |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

---

### CourseEnrollment

| 필드 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | |
| course_id | UUID | FK(Course) NOT NULL | |
| user_id | UUID | FK(User) NOT NULL | |
| role | ENUM('teacher','student') | NOT NULL | 해당 수업에서의 역할 |
| synced_at | TIMESTAMPTZ | NULL | Classroom 동기화 시각 |

**UNIQUE(course_id, user_id)**

---

### ProblemSet

| 필드 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | |
| name | VARCHAR(500) | NOT NULL | 문제 세트 이름 |
| course_id | UUID | FK(Course) NOT NULL | 속한 수업 |
| created_by | UUID | FK(User) NOT NULL | 생성 교사 |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

---

### ClassroomAssignment

| 필드 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | |
| classroom_coursework_id | VARCHAR(255) | UNIQUE NOT NULL | Google Classroom courseWork ID |
| course_id | UUID | FK(Course) NOT NULL | |
| problem_set_id | UUID | FK(ProblemSet) UNIQUE NULL | 연결된 문제 세트 (1:1) |
| title | VARCHAR(500) | NOT NULL | 과제 제목 |
| max_points | NUMERIC(10,2) | NULL | Google Classroom 배점 |
| scheduled_open_at | TIMESTAMPTZ | NULL | 예약 공개 시각 (null = 즉시 공개) |
| due_at | TIMESTAMPTZ | NULL | 마감 시각 |
| allow_late_submission | BOOLEAN | NOT NULL DEFAULT false | 마감 후 제출 허용 여부 (교사 설정) |
| synced_at | TIMESTAMPTZ | NULL | 마지막 Classroom 동기화 시각 |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

**비즈니스 규칙**:
- `problem_set_id`가 null이면 아직 온라인 저지와 연동되지 않은 상태.
- `scheduled_open_at` < `due_at` 유효성 검사 필수.

---

### StudentAssignmentExtension

| 필드 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | |
| assignment_id | UUID | FK(ClassroomAssignment) NOT NULL | |
| student_id | UUID | FK(User) NOT NULL | |
| extended_due_at | TIMESTAMPTZ | NOT NULL | 개별 연장 마감 시각 |
| synced_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

**UNIQUE(assignment_id, student_id)**

---

### Problem

| 필드 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | |
| problem_set_id | UUID | FK(ProblemSet) NOT NULL | |
| display_order | INTEGER | NOT NULL | 문제 세트 내 순서 (1-based) |
| title | VARCHAR(500) | NOT NULL | 문제 제목 |
| description_md | TEXT | NOT NULL | 문제 설명 (Markdown) |
| input_description_md | TEXT | NULL | 입력 형식 설명 |
| output_description_md | TEXT | NULL | 출력 형식 설명 |
| time_limit_sec | NUMERIC(5,2) | NOT NULL DEFAULT 1.0 | 실행 시간 제한 (초) |
| memory_limit_mb | INTEGER | NOT NULL DEFAULT 256 | 메모리 제한 (MB) |
| max_points | NUMERIC(10,2) | NOT NULL | 이 문제의 최대 배점 |
| allowed_languages | VARCHAR[] | NOT NULL | 허용 언어 목록 (예: ['python3','java17','cpp17','c17']) |
| created_by | UUID | FK(User) NOT NULL | |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

**비즈니스 규칙**:
- `display_order` 는 문제 세트 내 UNIQUE.
- `time_limit_sec` 범위: 0.5 ~ 10.0.
- `memory_limit_mb` 범위: 32 ~ 512.
- `max_points` > 0 필수.

---

### AttemptScoreTier

| 필드 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | |
| problem_id | UUID | FK(Problem) NOT NULL | |
| min_attempts | INTEGER | NOT NULL | 구간 최소 시도 횟수 (포함) |
| max_attempts | INTEGER | NULL | 구간 최대 시도 횟수 (포함, null = 무제한) |
| score_ratio | NUMERIC(5,2) | NOT NULL | 점수 비율 (0.00 ~ 100.00) |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

**비즈니스 규칙**:
- `min_attempts` >= 1, `max_attempts` > `min_attempts` (null 제외).
- 동일 problem_id 내에서 구간이 겹치면 안 됨 (저장 시 서버 검사).
- `max_attempts = null` 인 구간은 문제당 최대 1개 허용.
- 어떤 구간에도 해당하지 않는 시도 횟수는 0점 처리.
- 예시: (1,5,100.0), (6,10,80.0), (11,null,60.0).

---

### TestCase

| 필드 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | |
| problem_id | UUID | FK(Problem) NOT NULL | |
| display_order | INTEGER | NOT NULL | |
| input_storage_key | TEXT | NOT NULL | 입력 파일 스토리지 키 |
| expected_output_storage_key | TEXT | NOT NULL | 예상 출력 파일 스토리지 키 |
| is_public | BOOLEAN | NOT NULL DEFAULT false | 학생에게 입출력 공개 여부 |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

**비즈니스 규칙**:
- 파일 내용은 DB에 저장하지 않고 파일 스토리지(로컬 볼륨 or S3)에 저장, DB는 키만 보관.
- 문제당 1~100개 제한.

---

### Submission

| 필드 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | |
| student_id | UUID | FK(User) NOT NULL | |
| problem_id | UUID | FK(Problem) NOT NULL | |
| code | TEXT | NOT NULL | 제출 코드 |
| language | VARCHAR(20) | NOT NULL | 사용 언어 코드 |
| submitted_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |
| is_late | BOOLEAN | NOT NULL DEFAULT false | 마감 후 제출 여부 |
| attempt_number | INTEGER | NOT NULL | 이 제출 시점의 시도 횟수 |
| verdict | ENUM | NULL | 채점 결과 (null = 채점 중) |
| test_case_results | JSONB | NULL | 각 테스트 케이스 결과 배열 |
| score | NUMERIC(10,2) | NULL | 획득 점수 |
| judged_at | TIMESTAMPTZ | NULL | 채점 완료 시각 |

**verdict ENUM 값**: `PENDING`, `ACCEPTED`, `WRONG_ANSWER`, `TIME_LIMIT_EXCEEDED`, `MEMORY_LIMIT_EXCEEDED`, `RUNTIME_ERROR`, `COMPILATION_ERROR`

**test_case_results JSONB 형식**:
```json
[
  { "test_case_id": "uuid", "order": 1, "verdict": "ACCEPTED", "time_ms": 120, "memory_mb": 12 },
  { "test_case_id": "uuid", "order": 2, "verdict": "WRONG_ANSWER", "time_ms": 95, "memory_mb": 10 }
]
```

**비즈니스 규칙**:
- `attempt_number` 는 제출 시 `StudentProblemProgress.attempt_count` 를 원자적으로 +1 한 값.
- 이미 ACCEPTED 인 문제에 재제출해도 `attempt_number` 는 증가하지 않음.

---

### StudentProblemProgress

| 필드 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | |
| student_id | UUID | FK(User) NOT NULL | |
| problem_id | UUID | FK(Problem) NOT NULL | |
| attempt_count | INTEGER | NOT NULL DEFAULT 0 | 누적 유효 시도 횟수 |
| first_accepted_attempt | INTEGER | NULL | 최초 Accepted 시도 횟수 |
| final_score | NUMERIC(10,2) | NOT NULL DEFAULT 0 | 이 문제에서 획득한 점수 |
| accepted_at | TIMESTAMPTZ | NULL | 최초 Accepted 시각 |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

**UNIQUE(student_id, problem_id)**

**비즈니스 규칙**:
- `final_score` 는 최초 Accepted 시에만 설정되며 이후 변경 안 됨 (단, 교사가 소급 적용 선택 시 예외).
- `attempt_count` 증가는 DB 트랜잭션 + `SELECT FOR UPDATE` 로 원자성 보장.

---

### GradePassbackLog

| 필드 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | |
| student_id | UUID | FK(User) NOT NULL | |
| assignment_id | UUID | FK(ClassroomAssignment) NOT NULL | |
| score | NUMERIC(10,2) | NOT NULL | 반영 시도한 점수 |
| status | ENUM('pending','success','failed') | NOT NULL DEFAULT 'pending' | |
| attempt_count | INTEGER | NOT NULL DEFAULT 1 | 재시도 횟수 |
| last_attempted_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |
| error_message | TEXT | NULL | 실패 시 오류 메시지 |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

---

## 상태 전이

### Submission.verdict
```
(생성) → PENDING → ACCEPTED
                 → WRONG_ANSWER
                 → TIME_LIMIT_EXCEEDED
                 → MEMORY_LIMIT_EXCEEDED
                 → RUNTIME_ERROR
                 → COMPILATION_ERROR
```

### GradePassbackLog.status
```
pending → success
        → failed (재시도 3회 소진 후)
```

---

---

### SimilarityReport

| 필드 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID | PK | |
| assignment_id | UUID | FK(ClassroomAssignment) NOT NULL | |
| problem_id | UUID | FK(Problem) NOT NULL | |
| student_a_id | UUID | FK(User) NOT NULL | |
| student_b_id | UUID | FK(User) NOT NULL | |
| submission_a_id | UUID | FK(Submission) NOT NULL | 비교 대상 제출 (A) |
| submission_b_id | UUID | FK(Submission) NOT NULL | 비교 대상 제출 (B) |
| similarity_score | NUMERIC(5,2) | NOT NULL | 유사도 (0.00 ~ 100.00) |
| is_flagged | BOOLEAN | NOT NULL DEFAULT false | 임계값 초과 여부 |
| threshold_used | NUMERIC(5,2) | NOT NULL | 분석 시 적용된 임계값 |
| analyzed_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

**UNIQUE(assignment_id, problem_id, student_a_id, student_b_id)** — student_a_id < student_b_id 정렬 보장으로 (A,B)와 (B,A) 중복 방지.

**비즈니스 규칙**:
- 동일 과제/문제에 대해 분석을 재실행하면 기존 레코드를 덮어쓴다.
- 토큰 기반 비교: 변수명·문자열 리터럴 정규화 후 AST 구조 유사도 계산.

---

## 인덱스 전략

| 테이블 | 인덱스 컬럼 | 목적 |
|--------|------------|------|
| Submission | (student_id, problem_id, submitted_at DESC) | 학생별 제출 이력 조회 |
| Submission | (problem_id, verdict) | 교사 통계 집계 |
| StudentProblemProgress | (student_id, problem_id) | UNIQUE, 채점 시 빈번 조회 |
| GradePassbackLog | (status, last_attempted_at) | 재시도 대상 조회 |
| ClassroomAssignment | (classroom_coursework_id) | UNIQUE, Classroom 동기화 |
| SimilarityReport | (assignment_id, problem_id, is_flagged) | 교사 플래그 목록 조회 |
| SimilarityReport | (assignment_id, problem_id, similarity_score DESC) | 유사도 순 정렬 |
