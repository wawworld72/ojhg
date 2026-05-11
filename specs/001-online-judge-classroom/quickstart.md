# Quickstart: 로컬 개발 환경 구성

**전제 조건**: Docker, Docker Compose, Node.js 20+, Python 3.12+

---

## 1. 저장소 클론 및 환경 변수 설정

```bash
cp .env.example .env
# .env 파일에서 다음 값 설정:
# GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET — Google Cloud Console에서 발급
# ENCRYPTION_KEY — 32바이트 랜덤 문자열 (토큰 암호화용)
# SECRET_KEY — 세션 서명용 랜덤 문자열
```

## 2. Docker Compose로 전체 스택 실행

```bash
docker compose up -d
# 실행 서비스: postgres, redis, backend(FastAPI), frontend(Next.js), celery-worker
```

## 3. DB 마이그레이션

```bash
docker compose exec backend alembic upgrade head
```

## 4. 접속

- 프론트엔드: http://localhost:3000
- API 문서: http://localhost:8000/docs

---

## Google OAuth 로컬 설정

Google Cloud Console → OAuth 2.0 클라이언트 → 승인된 리디렉션 URI에 추가:
```
http://localhost:8000/api/v1/auth/google/callback
```
