from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://judge:judgepass@localhost:5432/onlinejudge"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"

    # GitHub OAuth
    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "http://localhost:8000/api/v1/github/callback"

    # Security
    secret_key: str = "dev-secret-key-change-in-prod"
    encryption_key: str = "dev-encryption-key-32bytes!!!"  # must be 32 bytes

    # App
    frontend_url: str = "http://localhost:3000"
    debug: bool = False

    # Testcase storage
    testcase_dir: str = "/app/testcases"

    # Judge sandbox
    sandbox_memory_limit_mb: int = 512
    sandbox_time_limit_sec: float = 10.0
    sandbox_pids_limit: int = 64

    @property
    def encryption_key_bytes(self) -> bytes:
        key = self.encryption_key.encode("utf-8")
        # Pad or truncate to exactly 32 bytes for AES-256
        return key[:32].ljust(32, b"\x00")


settings = Settings()
