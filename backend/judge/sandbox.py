"""Docker sandbox runner for code execution."""
from __future__ import annotations

import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings


LANGUAGE_CONFIG: dict[str, dict] = {
    "python3": {
        "image": "judge-python3:latest",
        "filename": "solution.py",
        "compile_cmd": None,
        "run_cmd": "timeout {time_limit} python3 solution.py",
    },
    "java17": {
        "image": "judge-java17:latest",
        "filename": "Solution.java",
        "compile_cmd": "javac Solution.java",
        "run_cmd": "timeout {time_limit} java -Xmx{memory_mb}m Solution",
    },
    "cpp17": {
        "image": "judge-cpp17:latest",
        "filename": "solution.cpp",
        "compile_cmd": "g++ -O2 -std=c++17 -o solution solution.cpp",
        "run_cmd": "timeout {time_limit} ./solution",
    },
    "c17": {
        "image": "judge-c17:latest",
        "filename": "solution.c",
        "compile_cmd": "gcc -O2 -std=c17 -o solution solution.c",
        "run_cmd": "timeout {time_limit} ./solution",
    },
}


@dataclass
class SandboxResult:
    verdict: str  # ACCEPTED | WRONG_ANSWER | TLE | MLE | RE | CE
    stdout: str
    stderr: str
    time_ms: int
    memory_mb: float
    compilation_error: str | None = None


def run_in_sandbox(
    language: str,
    code: str,
    input_data: str,
    time_limit_sec: float,
    memory_limit_mb: int,
) -> SandboxResult:
    """Run code in isolated Docker container and return execution result."""
    lang_cfg = LANGUAGE_CONFIG.get(language)
    if not lang_cfg:
        return SandboxResult(
            verdict="COMPILATION_ERROR",
            stdout="",
            stderr=f"Unsupported language: {language}",
            time_ms=0,
            memory_mb=0,
            compilation_error=f"Unsupported language: {language}",
        )

    container_name = f"judge-{uuid.uuid4().hex[:12]}"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        src_file = tmp / lang_cfg["filename"]
        src_file.write_text(code, encoding="utf-8")
        input_file = tmp / "input.txt"
        input_file.write_text(input_data, encoding="utf-8")

        # Build docker run command
        docker_cmd = [
            "docker", "run",
            "--name", container_name,
            "--rm",
            "--network", "none",
            "--read-only",
            "--tmpfs", "/tmp:size=32m",
            f"--cpus={1}",
            f"--memory={memory_limit_mb}m",
            f"--pids-limit={settings.sandbox_pids_limit}",
            "--user", "1001",
            "-v", f"{tmp}:/sandbox:ro",
            "-w", "/sandbox",
        ]

        # Compile step (Java/C/C++)
        if lang_cfg["compile_cmd"]:
            compile_cmd = lang_cfg["compile_cmd"]
            compile_result = subprocess.run(
                docker_cmd + [lang_cfg["image"], "sh", "-c", compile_cmd],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if compile_result.returncode != 0:
                return SandboxResult(
                    verdict="COMPILATION_ERROR",
                    stdout="",
                    stderr=compile_result.stderr,
                    time_ms=0,
                    memory_mb=0,
                    compilation_error=compile_result.stderr[:2000],
                )

        # Run step
        run_cmd = lang_cfg["run_cmd"].format(
            time_limit=time_limit_sec,
            memory_mb=memory_limit_mb,
        )
        full_run_cmd = f"{run_cmd} < /sandbox/input.txt"

        try:
            import time
            start = time.monotonic()
            run_result = subprocess.run(
                docker_cmd + [lang_cfg["image"], "sh", "-c", full_run_cmd],
                capture_output=True,
                text=True,
                timeout=time_limit_sec + 5,  # extra buffer for Docker overhead
            )
            elapsed_ms = int((time.monotonic() - start) * 1000)
        except subprocess.TimeoutExpired:
            subprocess.run(["docker", "stop", container_name], capture_output=True)
            return SandboxResult(
                verdict="TIME_LIMIT_EXCEEDED",
                stdout="",
                stderr="",
                time_ms=int(time_limit_sec * 1000),
                memory_mb=0,
            )

        # Interpret exit code
        # timeout command exits 124 on TLE
        if run_result.returncode == 124:
            verdict = "TIME_LIMIT_EXCEEDED"
        elif run_result.returncode == 137:
            # OOM kill
            verdict = "MEMORY_LIMIT_EXCEEDED"
        elif run_result.returncode != 0:
            verdict = "RUNTIME_ERROR"
        else:
            verdict = "RUN_OK"

        return SandboxResult(
            verdict=verdict,
            stdout=run_result.stdout,
            stderr=run_result.stderr,
            time_ms=elapsed_ms,
            memory_mb=0.0,  # Docker stats parsing omitted for brevity
        )
