# Research: Google Classroom-Integrated Online Judge

**Date**: 2026-05-11
**Branch**: `claude/implement-spec-kit-3P5ga`

---

## 1. Google Classroom 연동 방식

### Decision: Direct Google Classroom API (REST) + OAuth 2.0

**Rationale**:
- Google Classroom은 공식 REST API를 제공하며 과제(CourseWork), 수강생(Student), 성적(StudentSubmission) 전체를 CRUD할 수 있다.
- LTI(Learning Tools Interoperability) 방식은 Google Classroom이 공식 지원하지 않으므로 제외.
- Grade passback은 `courses.courseWork.studentSubmissions.patch` + `return` 로 처리.

**Alternatives considered**:
- LTI 1.3: Google Classroom이 공식 지원 안 함 → 제외.
- Google Forms API: 채점 자동화 불가 → 제외.

**주요 API 엔드포인트**:
- `courses.courseWork.get` — 과제 상세(예약 시각, 마감, 배점) 조회
- `courses.students.list` — 수강생 목록
- `courses.courseWork.studentSubmissions.patch` — 성적 기록
- `courses.courseWork.studentSubmissions.return` — 성적 반환(공개)
- `userProfiles.get` — 사용자 역할 확인

**일정 동기화 전략**: Classroom Pub/Sub 알림(Push Notification)은 Google Workspace Admin 설정 필요. 따라서 v1은 **주기적 폴링(15분 간격)** + 학생/교사 접근 시 **온-디맨드 동기화** 병행.

**필요 OAuth 스코프 (최소 원칙)**:
- `https://www.googleapis.com/auth/classroom.courses.readonly`
- `https://www.googleapis.com/auth/classroom.coursework.students`
- `https://www.googleapis.com/auth/classroom.rosters.readonly`
- `https://www.googleapis.com/auth/classroom.profile.emails`

---

## 2. 코드 실행 샌드박스

### Decision: 자체 Docker 컨테이너 샌드박스 (per-submission)

**Rationale**:
- Constitution "Security Isolation" 원칙 준수: 각 제출은 독립 컨테이너에서 실행.
- Judge0 (hosted) 는 외부 서비스 의존성이 크고 데이터 주권 문제 존재 → 제외.
- gVisor 또는 seccomp 기반 Docker 런타임으로 컨테이너 탈출 방지.

**샌드박스 구성**:
- 언어별 사전 빌드 이미지 (python:3.12-slim, openjdk:17-slim, gcc:13-slim)
- 네트워크 비활성화 (`--network none`)
- 읽기 전용 루트 파일시스템 + 임시 tmpfs `/tmp` (코드 실행 전용)
- CPU 제한: `--cpus 1`, 메모리: `--memory <limit>m`
- 실행 사용자: 비루트(uid 1001)
- 타임아웃: `timeout` 명령 + Docker stop 이중 보호

**Alternatives considered**:
- Judge0 SaaS: 외부 의존, 데이터 유출 위험 → 제외.
- Firecracker microVM: 운영 복잡도 과다, v1 범위 초과 → v2 고려.
- nsjail: 성숙도 높지만 Docker보다 운영 난이도 높음 → v2 고려.

---

## 3. 비동기 채점 아키텍처

### Decision: Redis + Celery (Python) 작업 큐

**Rationale**:
- 채점은 CPU 집약적이고 최대 30초 소요 → HTTP 요청 스레드에서 분리 필수.
- Redis는 이미 세션/캐시 용도로도 사용 → 단일 인프라 재사용.
- Celery는 Python 생태계 표준, 재시도/우선순위/모니터링(Flower) 지원.

**채점 흐름**:
```
학생 제출 → API (즉시 submission_id 반환) → Celery 큐 → Worker(Docker 실행)
→ DB 결과 저장 → WebSocket/SSE로 학생에게 푸시 → Classroom 성적 반영 태스크 큐잉
```

**Alternatives considered**:
- RabbitMQ: 메시지 보장이 더 강하나 Redis 중복 인프라 → 제외.
- Thread pool (동기): 채점 중 서버 블로킹, 확장 불가 → 제외.

---

## 4. 웹 프레임워크 및 기술 스택

### Decision

| 계층 | 선택 | 근거 |
|------|------|------|
| Backend API | Python + FastAPI | 비동기 지원, Pydantic 검증, OpenAPI 자동 생성, Celery와 동일 생태계 |
| Frontend | Next.js (React) | SSR로 SEO/초기 로딩, Google OAuth 흐름 처리 용이, TypeScript 타입 안전성 |
| DB | PostgreSQL 16 | 복잡한 관계형 데이터 모델, JSON 컬럼(테스트 케이스 결과 저장) |
| ORM | SQLAlchemy 2 (async) | FastAPI와 궁합, 마이그레이션(Alembic) 지원 |
| Cache/Queue broker | Redis 7 | 세션, Celery 브로커, 결과 백엔드 겸용 |
| 실시간 | Server-Sent Events (SSE) | WebSocket보다 단순, 채점 결과 단방향 푸시로 충분 |
| 컨테이너 오케스트레이션 | Docker Compose (로컬), 단일 서버 Docker (v1 prod) | 초기 규모에 적합, K8s는 v2 이후 |

---

## 5. 인증 흐름

### Decision: Google OAuth 2.0 Authorization Code Flow + 서버 세션

**흐름**:
1. 학생/교사가 "Google로 로그인" 클릭 → Google OAuth 동의 화면
2. Google이 인증 코드를 백엔드 콜백 URL로 전달
3. 백엔드가 access_token + refresh_token 교환, Google 프로필 조회
4. User 레코드 upsert, 서버 세션(Redis) 발급
5. Classroom API 호출 시 refresh_token으로 access_token 갱신

**Google refresh_token 보관**: 서버 DB에 암호화 저장 (AES-256). 클라이언트에 절대 노출 안 함.

---

## 6. 시도 횟수 기반 점수 구간 구현 전략

**Decision**: 제출 시점에 `StudentProblemProgress.attempt_count`를 원자적으로 증가시키고, 최초 Accepted 시 해당 시점 횟수로 구간 매핑 후 점수 고정.

- `attempt_count` 증가는 DB 트랜잭션 내 `SELECT FOR UPDATE`로 race condition 방지.
- Accepted 이후 재제출은 attempt_count를 증가시키지 않고 점수도 변경하지 않는다.
- 구간 겹침 방지: 저장 시 서버에서 유효성 검사 (min < max, 구간 간 overlap 없음).

---

## 7. 프로젝트 구조 결정

**Decision**: Option 2 (Web application) — backend + frontend 분리 모노레포

```
backend/    — FastAPI + Celery (Python)
frontend/   — Next.js (TypeScript)
judge/      — 샌드박스 실행 스크립트 + 언어별 Dockerfile
infra/      — Docker Compose, Nginx 설정
```
