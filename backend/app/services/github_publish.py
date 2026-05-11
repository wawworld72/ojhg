"""GitHub publish service: push student submissions as branches."""
import os
import re
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text[:50]


async def ensure_github_repo(
    github_username: str,
    access_token: str,
    repo_name: str,
) -> str:
    """Create the GitHub repo if it doesn't exist. Returns HTTPS clone URL."""
    import httpx

    headers = {
        "Authorization": f"token {access_token}",
        "Accept": "application/vnd.github+json",
    }
    async with httpx.AsyncClient() as client:
        check = await client.get(
            f"https://api.github.com/repos/{github_username}/{repo_name}",
            headers=headers,
        )
        if check.status_code == 200:
            return check.json()["clone_url"]

        resp = await client.post(
            "https://api.github.com/user/repos",
            headers=headers,
            json={"name": repo_name, "private": True, "auto_init": True},
        )
        resp.raise_for_status()
        return resp.json()["clone_url"]


async def push_student_submissions(
    student_id: uuid.UUID,
    assignment_slug: str,
    problem_slug: str,
    student_slug: str,
    submissions: list[dict],
    clone_url_with_token: str,
    repo_url: str,
) -> dict:
    """Push all submissions for a student×problem as commits on a branch."""
    branch_name = f"submissions/{assignment_slug}/{problem_slug}/{student_slug}"

    with tempfile.TemporaryDirectory() as tmpdir:
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}

        subprocess.run(
            ["git", "clone", "--depth=1", clone_url_with_token, tmpdir],
            check=True, env=env, capture_output=True,
        )

        # Create branch
        subprocess.run(
            ["git", "-C", tmpdir, "checkout", "-b", branch_name],
            check=True, env=env, capture_output=True,
        )

        ext_map = {
            "python3": ".py", "java17": ".java",
            "cpp17": ".cpp", "c17": ".c",
        }
        commits_pushed = 0
        for sub in sorted(submissions, key=lambda s: s["attempt_number"]):
            ext = ext_map.get(sub["language"], ".txt")
            code_file = Path(tmpdir) / f"solution{ext}"
            code_file.write_text(sub["code"], encoding="utf-8")

            subprocess.run(
                ["git", "-C", tmpdir, "add", str(code_file)],
                check=True, env=env, capture_output=True,
            )

            msg = (
                f"[Attempt #{sub['attempt_number']}] {sub['verdict']} — "
                f"{sub['submitted_at']}\n"
                f"Score: {sub['score']} | Language: {sub['language']}"
            )
            subprocess.run(
                ["git", "-C", tmpdir, "commit", "--allow-empty", "-m", msg,
                 "--author", f"{student_slug} <{student_slug}@ojhg>"],
                check=True, env=env, capture_output=True,
            )
            commits_pushed += 1

        subprocess.run(
            ["git", "-C", tmpdir, "push", clone_url_with_token, branch_name],
            check=True, env=env, capture_output=True,
        )

    branch_url = f"{repo_url}/tree/{branch_name}"
    return {
        "branch_name": branch_name,
        "branch_url": branch_url,
        "commits_pushed": commits_pushed,
    }
