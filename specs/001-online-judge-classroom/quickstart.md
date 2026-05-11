# Quickstart: Mac 로컬 실행 가이드 (학교 내부망 수업용)

**전제 조건**: Docker Desktop (Apple Silicon 지원), Node.js 20+, Python 3.12+

---

## 0. Docker Desktop 리소스 설정 (필수)

Docker Desktop → Settings → Resources:
- **Memory**: 12GB 이상
- **CPUs**: 8개 이상
- **Swap**: 2GB

---

## 1. 환경 변수 설정

```bash
cp .env.example .env
# .env 필수 항목:
# GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET  — Google Cloud Console 발급
# ENCRYPTION_KEY  — 32바이트 랜덤 문자열 (openssl rand -hex 32)
# SECRET_KEY      — 세션 서명용 (openssl rand -hex 32)
# ALLOWED_HOSTS   — 내부망 IP 주소 (예: 192.168.1.100)
```

## 2. Docker Compose로 전체 스택 실행

```bash
docker compose up -d
# 실행 서비스: postgres, redis, backend(FastAPI), frontend(Next.js), celery-worker(×8)
```

## 3. DB 마이그레이션

```bash
docker compose exec backend alembic upgrade head
```

## 4. Cloudflare Tunnel 설정 (내부망 + 외부망 학생 모두 지원)

일부 학생이 외부 망을 사용하는 경우를 위해 Cloudflare Tunnel을 사용합니다.
내부망 학생도 동일한 URL로 접속하므로 URL을 하나로 통일할 수 있습니다.

```bash
# cloudflared 설치 (Mac)
brew install cloudflare/cloudflare/cloudflared

# Cloudflare 로그인 (최초 1회)
cloudflared tunnel login

# 터널 생성 (최초 1회)
cloudflared tunnel create ojhg-judge

# 터널 실행 (수업 시작 시마다)
cloudflared tunnel --url http://localhost:3000 run ojhg-judge
# → https://ojhg-judge.yourdomain.com 과 같은 고정 URL 생성
```

> **무료 계정 사용 시**: `cloudflared tunnel --url http://localhost:3000` 으로 임시 URL 생성 가능 (`*.trycloudflare.com`). 수업마다 URL이 바뀌므로 Cloudflare 계정 연동 후 고정 도메인 사용 권장.

## 5. Google OAuth 콜백 등록

Google Cloud Console → OAuth 2.0 클라이언트 → 승인된 리디렉션 URI:
```
https://<cloudflare-tunnel-domain>/api/v1/auth/google/callback
```
> Cloudflare Tunnel 도메인은 고정이므로 최초 1회만 등록하면 됩니다.

## 6. 수업 종료 후 DB 백업

```bash
docker compose exec postgres pg_dump -U postgres ojhg > backup_$(date +%Y%m%d).sql
# 백업 파일을 iCloud Drive 또는 외장 드라이브에 복사
```

---

## VPS 이전 시 (원격 수업 전환)

```bash
# Hetzner CX42 등 Linux 서버에서 동일하게 실행
# .env의 ALLOWED_HOSTS를 도메인으로 변경
docker compose -f docker-compose.prod.yml up -d
```
