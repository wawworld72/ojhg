# Quickstart: Mac 로컬 실행 가이드 (학교 내부망 수업용)

**전제 조건**: Docker Desktop (Apple Silicon 지원), Node.js 20+, Python 3.12+

---

## 0. Google Cloud Console 사전 설정 (최초 1회)

> 코드 배포 전에 완료해야 합니다. Google 계정은 학교 Google Workspace 관리자 계정을 권장합니다.

### 0-1. Google Cloud 프로젝트 생성

1. [console.cloud.google.com](https://console.cloud.google.com) 접속
2. 상단 프로젝트 선택 → **새 프로젝트** → 이름 입력 (예: `ojhg-judge`) → 만들기

### 0-2. 필요한 API 활성화

**API 및 서비스 → 라이브러리**에서 아래 두 API를 검색 후 각각 **사용 설정**:

| API | 용도 |
|-----|------|
| **Google Classroom API** | 과제 목록 조회, 성적 반영 |
| **People API** | 로그인 사용자 프로필(이름, 사진) 조회 |

### 0-3. OAuth 동의 화면 구성

**API 및 서비스 → OAuth 동의 화면**:

- 사용자 유형: **내부** (학교 Google Workspace 전용) — 심사 없이 즉시 사용 가능
  - 개인 Gmail 계정만 있다면 **외부** 선택 후 테스트 사용자 추가
- 앱 이름, 지원 이메일 입력 후 저장
- **스코프 추가** (민감한 범위 포함):

```
openid
email
profile
https://www.googleapis.com/auth/classroom.courses.readonly
https://www.googleapis.com/auth/classroom.coursework.students
https://www.googleapis.com/auth/classroom.rosters.readonly
```

### 0-4. OAuth 2.0 클라이언트 ID 발급

**API 및 서비스 → 사용자 인증 정보 → 사용자 인증 정보 만들기 → OAuth 클라이언트 ID**:

- 애플리케이션 유형: **웹 애플리케이션**
- 승인된 리디렉션 URI 추가:

```
# 로컬 개발용
http://localhost:8000/api/v1/auth/google/callback

# Cloudflare Tunnel 사용 시 (고정 도메인 설정 후 추가)
https://<cloudflare-tunnel-domain>/api/v1/auth/google/callback
```

- **만들기** 클릭 → `클라이언트 ID`와 `클라이언트 보안 비밀번호`를 복사해 두기

> **주의**: 클라이언트 보안 비밀번호는 창을 닫으면 다시 볼 수 없으므로 즉시 저장하세요.

---

## 1. Docker Desktop 리소스 설정 (필수)

Docker Desktop → Settings → Resources:
- **Memory**: 12GB 이상
- **CPUs**: 8개 이상
- **Swap**: 2GB

---

## 1. 환경 변수 설정

```bash
cd infra
cp .env.example .env
```

`.env` 파일을 열어 아래 항목을 채웁니다:

```bash
# 0-4 단계에서 복사한 값
GOOGLE_CLIENT_ID=123456789-xxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxx

# 각각 openssl rand -hex 32 로 생성
ENCRYPTION_KEY=<32바이트 hex>   # refresh_token AES-256 암호화 키
SECRET_KEY=<32바이트 hex>       # 세션 서명 키

# GitHub Publish 기능 사용 시 (선택)
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=

# 내부망 접속 IP (Cloudflare Tunnel 사용 시 터널 도메인으로 대체)
FRONTEND_URL=http://localhost:3000
```

키 생성 명령어:
```bash
openssl rand -hex 32   # ENCRYPTION_KEY 용
openssl rand -hex 32   # SECRET_KEY 용
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
