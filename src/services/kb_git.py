"""Git workflow for Knowledge Base content repository."""

from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from config import settings


try:
    from git import Repo
    from git.exc import GitCommandError, InvalidGitRepositoryError
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "GitPython is required for KB Git workflow. "
        "Install it: pip install GitPython==3.1.43"
    ) from exc


class KbGitError(Exception):
    """Base exception for KB Git operations."""

    pass


class KbGitService:
    """Manage the KB Content Git repository working copy."""

    def __init__(
        self,
        repo_url: str | None = None,
        repo_path: str | Path | None = None,
        enabled: bool | None = None,
        default_branch: str | None = None,
    ):
        self.repo_url = (repo_url or settings.kb_content_repo_url).strip()
        self.repo_path = Path(repo_path or settings.kb_content_repo_path).resolve()
        self.enabled = enabled if enabled is not None else settings.kb_content_git_enabled
        self.default_branch = default_branch or settings.kb_content_default_branch or "main"
        self._repo: Repo | None = None

    # ------------------------------------------------------------------
    # Repo lifecycle
    # ------------------------------------------------------------------

    def open_repo(self) -> Repo:
        """Return an opened Repo, cloning if necessary and enabled."""
        if self._repo is not None:
            return self._repo

        self.repo_path.mkdir(parents=True, exist_ok=True)

        if (self.repo_path / ".git").exists():
            try:
                self._repo = Repo(self.repo_path)
                return self._repo
            except InvalidGitRepositoryError as exc:
                raise KbGitError(f"Invalid git repository at {self.repo_path}") from exc

        if not self.enabled or not self.repo_url:
            # Initialize a local repo so we can still use Git tooling locally.
            self._repo = Repo.init(self.repo_path)
            self._create_initial_commit_if_empty()
            return self._repo

        try:
            self._repo = Repo.clone_from(
                self.repo_url,
                self.repo_path,
                branch=self.default_branch,
                multi_options=["--single-branch"],
            )
        except GitCommandError as exc:
            raise KbGitError(f"Failed to clone KB content repo: {exc}") from exc

        return self._repo

    def _create_initial_commit_if_empty(self) -> None:
        """Create README if the freshly initialized repo is empty."""
        repo = self._repo
        if repo is None:
            return
        if not repo.head.is_valid():
            readme = self.repo_path / "README.md"
            readme.parent.mkdir(parents=True, exist_ok=True)
            if not readme.exists():
                readme.write_text(
                    "# AI Curator Knowledge Base Content\n\nSource documents storage.\n",
                    encoding="utf-8",
                )
            repo.index.add([str(readme.relative_to(self.repo_path))])
            repo.index.commit("init(kb-content): local content repository")

    def pull(self) -> None:
        """Pull the latest changes if the repo has a remote."""
        repo = self.open_repo()
        if not repo.remotes:
            return
        try:
            origin = repo.remotes.origin
            origin.pull(self.default_branch)
        except GitCommandError as exc:
            raise KbGitError(f"Failed to pull KB content repo: {exc}") from exc

    # ------------------------------------------------------------------
    # Content paths
    # ------------------------------------------------------------------

    def _relative_path(self, absolute_or_relative: str | Path) -> Path:
        """Return a path relative to the repo root."""
        path = Path(absolute_or_relative)
        try:
            return path.relative_to(self.repo_path.resolve())
        except ValueError:
            return path

    def content_path(
        self,
        document_type: str,
        course_id: int | None,
        filename: str,
    ) -> Path:
        """Build the canonical path for a KB source document."""
        parts: List[str] = ["courses"]
        if course_id is not None:
            parts.append(str(course_id))
        parts.append(document_type + "s")
        directory = self.repo_path / Path(*parts)
        directory.mkdir(parents=True, exist_ok=True)
        return directory / Path(filename).name

    # ------------------------------------------------------------------
    # Add / commit / push
    # ------------------------------------------------------------------

    def add_commit_push(
        self,
        file_path: str | Path,
        message: str,
        author_name: str = "AI Curator",
        author_email: str = "ai-curator@system.local",
    ) -> Dict[str, Any]:
        """Stage a file, commit it and optionally push to remote."""
        repo = self.open_repo()
        self.pull()

        file_path = Path(file_path)
        rel_path = self._relative_path(file_path)

        if not file_path.exists():
            raise KbGitError(f"File not found: {file_path}")

        file_path = file_path.resolve()
        self.repo_path = self.repo_path.resolve()
        rel_path = file_path.relative_to(self.repo_path)

        repo.index.add([str(rel_path)])

        if not repo.is_dirty(index=True, working_tree=False, untracked_files=False):
            # Nothing staged; still try to push any unpushed commits.
            self._push_if_remote(repo)
            return {
                "committed": False,
                "commit_hash": str(repo.head.commit.hexsha),
                "message": "No changes to commit",
            }

        from git import Actor

        actor = Actor(author_name, author_email)
        commit = repo.index.commit(
            message,
            author=actor,
            committer=actor,
            commit_date=datetime.now(timezone.utc),
        )

        self._push_if_remote(repo)

        return {
            "committed": True,
            "commit_hash": commit.hexsha,
            "author_name": author_name,
            "author_email": author_email,
            "message": message,
            "committed_at": commit.committed_datetime.isoformat(),
            "path": str(rel_path),
        }

    def _push_if_remote(self, repo: Repo) -> None:
        """Push current branch if remote is configured."""
        if not repo.remotes:
            return
        try:
            repo.remotes.origin.push(refspec=f"HEAD:{self.default_branch}")
        except GitCommandError as exc:
            raise KbGitError(f"Failed to push KB content repo: {exc}") from exc

    # ------------------------------------------------------------------
    # History / metadata
    # ------------------------------------------------------------------

    def get_file_history(self, path: str | Path, limit: int = 20) -> List[Dict[str, Any]]:
        """Return recent Git history for a file."""
        repo = self.open_repo()
        rel_path = str(self._relative_path(path))
        try:
            commits = list(repo.iter_commits(paths=rel_path, max_count=limit))
        except GitCommandError:
            return []

        result: List[Dict[str, Any]] = []
        for commit in commits:
            result.append(
                {
                    "commit_hash": commit.hexsha,
                    "author_name": commit.author.name,
                    "author_email": commit.author.email,
                    "message": commit.message.strip(),
                    "committed_at": (
                        commit.committed_datetime.isoformat() if commit.committed_datetime else None
                    ),
                }
            )
        return result

    def get_blob_hash(self, path: str | Path, commit_hash: str | None = None) -> str | None:
        """Return Git blob hash for a file at a specific commit or HEAD."""
        repo = self.open_repo()
        rel_path = str(self._relative_path(path))
        try:
            if commit_hash:
                commit = repo.commit(commit_hash)
            else:
                commit = repo.head.commit
            blob = commit.tree / rel_path
            return str(blob.hexsha) if blob else None
        except (KeyError, ValueError, GitCommandError):
            return None

    def get_file_at_commit(
        self,
        path: str | Path,
        commit_hash: str,
        max_bytes: int = 262144,
    ) -> bytes | None:
        """Return raw file contents at a specific commit."""
        repo = self.open_repo()
        rel_path = str(self._relative_path(path))
        try:
            commit = repo.commit(commit_hash)
            blob = commit.tree / rel_path
            data = blob.data_stream.read()
            return data[:max_bytes]
        except (KeyError, ValueError, GitCommandError):
            return None

    # ------------------------------------------------------------------
    # Local-only helpers for non-Git mode
    # ------------------------------------------------------------------

    def is_git_mode(self) -> bool:
        """Return True when remote Git workflow is enabled."""
        return self.enabled and bool(self.repo_url)


__all__ = ["KbGitService", "KbGitError"]
