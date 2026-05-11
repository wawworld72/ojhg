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

## 7. 인프라 — 단일 VPS vs GitHub/PaaS

### Decision: 단일 Linux VPS (Docker Compose) — Hetzner CX32 권장

**GitHub만으로 불가한 이유**:
- 상시 실행 웹 서버(FastAPI), PostgreSQL, Redis, Celery 워커 모두 GitHub에서 제공 불가.
- **결정적 제약**: 학생 코드 격리 실행을 위한 Docker 데몬 접근이 GitHub Actions/Pages/Codespaces 어디에서도 허용되지 않음.
- Railway, Render 등 PaaS도 Docker-in-Docker(DinD) 를 제한적으로만 허용하여 샌드박스 구현 불가.

**실제 수업 부하 계산 (50명 × 5문제 × 20시도, 30~60분)**:
```
최대 총 제출: 5,000건
30분 수업 기준 평균: ~167건/분 = 2.8건/초
채점 1건 평균 처리 시간: 5~10초 (언어·문제 복잡도 따라 다름)
필요 동시 채점 슬롯: 2.8건/초 × 10초 = 최대 28개
```

**서버 사양 재검토**:

| 옵션 | vCPU | RAM | 동시 채점 | 평균 대기 | 월 비용 |
|------|------|-----|----------|----------|---------|
| CX32 | 4 | 8GB | 4개 | ~7분 ❌ | €8 |
| **CX42** | **8** | **16GB** | **8개** | **~3.5분** ✅ | **€18** |
| CX52 | 16 | 32GB | 16개 | ~1.7분 | €38 |

**권장: Hetzner CX42 (8 vCPU / 16GB / €18/월)**
- 8개 Celery 워커 병렬 채점 → 평균 대기 3~4분 수용 가능
- 채점 컨테이너 8개 × 256MB = 2GB + OS/앱 오버헤드 → 16GB 충분
- 수업 후 Publish (5,000 커밋 git push): Celery 10개 병렬 → ~5분 내 완료

**배포 전략**:
- 단일 VPS에 Docker Compose (`docker-compose.prod.yml`)로 전체 스택 실행
- Nginx 리버스 프록시 → Let's Encrypt SSL
- GitHub Actions로 CI/CD: 테스트 통과 시 VPS에 SSH 배포 자동화
- 데이터 백업: PostgreSQL 일 1회 덤프를 외부 스토리지(Hetzner Object Storage)에 보관

**Alternatives considered**:
- Railway/Render: DinD 샌드박스 불가 → 제외.
- Google Cloud Run: 상시 실행 서버가 아니라 cold start 문제, Docker 소켓 마운트 불가 → 제외.
- GitHub Actions 자체 호스팅: 코드 제출 요청마다 Actions runner 실행 불가 → 제외.

---

## 8. GitHub Publish — 커밋 히스토리 업로드 방식

### Decision: GitHub Git Data API로 학생별 브랜치에 순차 커밋 생성

**브랜치 구조 — 문제(Problem) 단위 분리**:
```
repo: {target-repo-name}  (교사 GitHub 계정)

  # 문제별로 브랜치 분리 → git log = 단일 문제 순수 풀이 이력
  branch: submissions/hw-01/problem-1-sort/alice-kim
    commit "[#1] WA  | python3 | 2026-05-11T14:00Z"  ← solution.py
    commit "[#2] WA  | python3 | 2026-05-11T14:15Z"  ← solution.py
    commit "[#3] AC ✓| python3 | 2026-05-11T14:30Z | Score: 100/100"

  branch: submissions/hw-01/problem-2-dp/alice-kim
    commit "[#1] WA  | java17  | 2026-05-11T15:00Z"
    commit "[#2] AC ✓| java17  | 2026-05-11T15:20Z | Score: 80/100"

  branch: submissions/hw-01/problem-1-sort/bob-lee   ← bob 전용, alice와 완전 독립
    commit "[#1] WA  | cpp17   | ..."
    ...
```

**왜 과제(Assignment) 단위 브랜치가 아닌가**:
- 과제 단위 브랜치에 여러 문제 커밋이 섞이면 `git log`가 문제1/문제2 커밋이 
  시간 순으로 뒤섞여 특정 문제의 풀이 과정만 추적하기 어려움.
- 문제 단위 분리 시 브랜치 수 = 학생 수 × 문제 수 (50명 × 5문제 = 250개).
  GitHub은 수천 개 브랜치를 처리하므로 전혀 문제없음.

**브랜치 간 독립성 (충돌 없음)**:
- Git 브랜치는 독립 포인터; 브랜치 A 커밋이 브랜치 B에 물리적으로 영향 없음.
- 50명 동시 Publish 중 서로 다른 브랜치 ref를 갱신하므로 race condition 불가.

**커밋 생성 흐름 (Git Data API)**:
1. `GET /repos/{owner}/{repo}/git/refs/heads/{branch}` — 브랜치 최신 커밋 SHA 조회 (없으면 main에서 분기)
2. `POST /repos/{owner}/{repo}/git/blobs` — 코드 파일 blob 생성
3. `POST /repos/{owner}/{repo}/git/trees` — 새 tree 생성 (blob 포함)
4. `POST /repos/{owner}/{repo}/git/commits` — 커밋 생성 (parent: 이전 커밋 SHA)
5. `PATCH /repos/{owner}/{repo}/git/refs/heads/{branch}` — 브랜치 ref 갱신

**커밋 메시지 형식**:
```
[Attempt #3] Accepted ✓ — 2026-05-11T14:30:00Z
Score: 100/100 | Language: python3 | Time: 1.2s
```

**Rate Limit 분석 — REST API 방식은 불가**:
```
실제 수업 규모: 50명 × 5문제 × 20시도 = 5,000 커밋
REST API 방식: 5,000 커밋 × 5 API 호출 = 25,000 요청
GitHub 인증 한도: 5,000 요청/시간
→ 5배 초과 → REST API 방식 사용 불가
```

**해결: git push 프로토콜 사용 (Rate Limit 없음)**:
- VPS에서 로컬 git 작업 (clone → branch → commit → push)
- `git push`는 git 스마트 HTTP/SSH 프로토콜 사용 → REST API Rate Limit 미적용
- PyGit2 또는 subprocess git 명령으로 구현
- 학생별 병렬 처리 (Celery 10개 동시): 전체 업로드 ~5분 내 완료

**저장소 자동 생성**:
- 저장소 없으면 `POST /user/repos` 로 private 저장소 자동 생성
- 생성 시 README에 수업명, 과제명 포함

**Alternatives considered**:
- 학생별 별도 저장소: 저장소 수 과다(50개), 관리 복잡 → 제외.
- main 브랜치 직접 커밋: 모든 학생 커밋이 섞여 이력 추적 불가 → 제외.
- ZIP 업로드: git 히스토리 없어 리뷰 기능 활용 불가 → 제외.

---

## 9. 프로젝트 구조 결정

**Decision**: Option 2 (Web application) — backend + frontend 분리 모노레포

```
backend/    — FastAPI + Celery (Python)
frontend/   — Next.js (TypeScript)
judge/      — 샌드박스 실행 스크립트 + 언어별 Dockerfile
infra/      — Docker Compose, Nginx 설정
```
