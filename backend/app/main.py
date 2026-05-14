import logging
import logging.config
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings

logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "logging.Formatter",
            "fmt": '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"%(extra_fields)s}',
        },
        "standard": {
            "format": "%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "app": {"level": "DEBUG" if settings.debug else "INFO"},
        "uvicorn": {"level": "INFO"},
    },
})

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Online Judge API",
    version="1.0.0",
    docs_url="/api/docs" if settings.debug else None,
    redoc_url=None,
)

_cors_origins = [settings.frontend_url, "http://localhost", "http://localhost:80"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    https_only=not settings.debug,
    same_site="lax",
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    try:
        user_id = request.session.get("user_id", "-")
    except AssertionError:
        user_id = "-"
    logger.info(
        "request start method=%s path=%s",
        request.method,
        request.url.path,
        extra={"request_id": request_id, "user_id": user_id},
    )
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request end status=%d",
        response.status_code,
        extra={"request_id": request_id},
    )
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc, extra={"request_id": getattr(request.state, "request_id", None)})
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred", "details": None}},
    )


# Import and register routers
from app.api.v1 import auth, courses, github, problems, problem_sets, similarity, submissions  # noqa: E402

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(courses.router, prefix="/api/v1", tags=["courses"])
app.include_router(problem_sets.router, prefix="/api/v1", tags=["problem-sets"])
app.include_router(problems.router, prefix="/api/v1", tags=["problems"])
app.include_router(submissions.router, prefix="/api/v1", tags=["submissions"])
app.include_router(github.router, prefix="/api/v1/github", tags=["github"])
app.include_router(similarity.router, prefix="/api/v1", tags=["similarity"])


@app.get("/health")
async def health_check():
    return {"status": "ok"}
