# Implementation Plan: Google Classroom-Integrated Online Judge

**Branch**: `claude/implement-spec-kit-3P5ga` | **Date**: 2026-05-11 | **Spec**: [spec.md](spec.md)

## Summary

구글 클래스룸 과제와 연동하여 학생이 여러 문제를 코드로 제출하면 자동 채점하고, 시도 횟수 기반 점수 구간에 따른 최종 성적을 Classroom 성적부에 자동 반영하는 웹 서비스.

기술 접근: Python/FastAPI 백엔드 + Next.js 프론트엔드 분리 구조, Docker 샌드박스 격리 채점, Celery/Redis 비동기 큐, Google Classroom REST API 직접 연동.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript / Node.js 20 (frontend)
**Primary Dependencies**: FastAPI, SQLAlchemy 2 (async), Celery, google-auth-oauthlib, Next.js 14, React 18
**Storage**: PostgreSQL 16 (주 데이터), Redis 7 (세션, Celery 브로커/결과), 로컬 볼륨 (테스트 케이스 파일)
**Testing**: pytest + pytest-asyncio (backend), Jest + Testing Library (frontend), Docker-in-Docker (sandbox integration)
**Target Platform**: Linux 서버 (Docker Compose), 데스크탑 브라우저 (Chrome/Firefox/Edge 최신)
**Project Type**: Web application (backend API + frontend SPA + async worker)
**Performance Goals**: 채점 결과 30초 이내, 동시 제출 50건 처리, Classroom 성적 반영 5분 이내
**Constraints**: 샌드박스 컨테이너 메모리 max 512MB, 실행 시간 max 10초, 코드 실행은 네트워크 완전 차단
**Scale/Scope**: 수업당 최대 200명 학생, 문제 세트당 최대 20문제, 테스트 케이스당 max 100개

## Constitution Check

| 원칙 | 상태 | 검증 |
|------|------|------|
| I. 정확성 & 공정성 | ✅ | Docker 샌드박스 동일 이미지 실행, 동일 시간/메모리 제한, Celery 단일 워커 순차 채점 |
| II. 보안 격리 | ✅ | `--network none`, 비루트 실행, `--pids-limit 64`, seccomp 프로필, 읽기 전용 루트 FS |
| III. Classroom 연동 충실성 | ✅ | 공식 Google Classroom REST API, OAuth2 최소 스코프, 멱등적 성적 반영 |
| IV. TDD | ✅ | 각 Phase의 단위/통합 테스트 선행 작성 후 구현 |
| V. 단순성 & 점진적 배포 | ✅ | 수직 슬라이스 단위(Phase별) 배포, 스페셜 저지/Firecracker는 v2 |

## Project Structure

### Documentation (this feature)

```text
specs/001-online-judge-classroom/
├── plan.md              ← 이 파일
├── research.md          ← Phase 0 완료
├── data-model.md        ← Phase 1 완료
├── quickstart.md        ← Phase 1 완료
├── contracts/
│   ├── api.md           ← Phase 1 완료
│   └── sandbox.md       ← Phase 1 완료
└── tasks.md             ← /speckit-tasks 생성 예정
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── main.py                    # FastAPI app entry
│   ├── core/
│   │   ├── config.py              # 환경 변수, 설정
│   │   ├── security.py            # 토큰 암호화, 세션
│   │   └── database.py            # SQLAlchemy async engine
│   ├── models/                    # SQLAlchemy ORM 모델
│   │   ├── user.py
│   │   ├── course.py
│   │   ├── problem_set.py
│   │   ├── problem.py
│   │   ├── submission.py
│   │   └── grade_passback.py
│   ├── schemas/                   # Pydantic 요청/응답 스키마
│   ├── api/
│   │   └── v1/
│   │       ├── auth.py
│   │       ├── courses.py
│   │       ├── problem_sets.py
│   │       ├── problems.py
│   │       └── submissions.py
│   ├── services/
│   │   ├── classroom_api.py       # Google Classroom API 클라이언트
│   │   ├── judge.py               # 채점 오케스트레이션
│   │   ├── grade_passback.py      # Classroom 성적 반영
│   │   └── scoring.py             # 시도 횟수 → 점수 계산
│   └── workers/
│       ├── celery_app.py
│       ├── judge_task.py          # 채점 Celery 태스크
│       └── grade_sync_task.py     # 성적 반영 Celery 태스크
├── judge/
│   ├── sandbox.py                 # Docker 실행 래퍼
│   ├── compare.py                 # 출력 비교 로직
│   └── images/
│       ├── python3/Dockerfile
│       ├── java17/Dockerfile
│       ├── cpp17/Dockerfile
│       └── c17/Dockerfile
├── alembic/                       # DB 마이그레이션
├── tests/
│   ├── unit/
│   ├── integration/
│   └── sandbox/
└── pyproject.toml

frontend/
├── src/
│   ├── app/                       # Next.js App Router
│   │   ├── layout.tsx
│   │   ├── page.tsx               # 홈 (수업 목록)
│   │   ├── assignments/[id]/
│   │   │   └── page.tsx           # 문제 세트 페이지 (학생)
│   │   └── teacher/
│   │       ├── problem-sets/      # 문제 세트 관리
│   │       └── stats/[setId]/     # 통계 대시보드
│   ├── components/
│   │   ├── editor/                # 코드 에디터 (Monaco)
│   │   ├── judge/                 # 채점 결과 UI
│   │   └── problem/               # 문제 뷰어
│   └── services/
│       └── api.ts                 # API 클라이언트
└── package.json

infra/
├── docker-compose.yml
├── docker-compose.prod.yml
├── nginx/
│   └── nginx.conf
└── .env.example
```

**Structure Decision**: 백엔드(FastAPI)와 프론트엔드(Next.js)를 분리된 디렉토리에 두되 단일 저장소(모노레포)로 관리. Docker Compose로 로컬 개발 환경 통합. 채점 이미지(judge/images/)는 별도 디렉토리로 분리하여 보안 검토 단위 명확화.

## Complexity Tracking

> Constitution Check 위반 없음 — 해당 사항 없음.
