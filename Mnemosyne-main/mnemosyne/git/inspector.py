import os
from pathlib import Path
from typing import List, Optional, Dict, Any
import git
from mnemosyne.memory.schemas import CommitMemory

class GitInspector:
    """Utility class to inspect git commits, staged diffs, and repository state."""

    @staticmethod
    def get_repo(repo_path: Optional[Path] = None) -> Optional[git.Repo]:
        try:
            target = repo_path or Path.cwd()
            return git.Repo(target, search_parent_directories=True)
        except (git.InvalidGitRepositoryError, git.NoSuchPathError):
            return None

    @classmethod
    def get_commit_history(cls, repo_path: Optional[Path] = None, max_commits: int = 10) -> List[CommitMemory]:
        repo = cls.get_repo(repo_path)
        if not repo or not repo.heads:
            return []

        commits = []
        try:
            for commit in repo.iter_commits(max_count=max_commits):
                changed_files = list(commit.stats.files.keys()) if commit.stats else []
                commit_mem = CommitMemory(
                    commit_hash=commit.hexsha,
                    author=str(commit.author),
                    summary=commit.summary or commit.message.split("\n")[0],
                    files_changed=changed_files,
                )
                commits.append(commit_mem)
        except Exception:
            pass
        return commits

    @classmethod
    def get_staged_diff(cls, repo_path: Optional[Path] = None) -> str:
        repo = cls.get_repo(repo_path)
        if not repo:
            return ""
        try:
            diffs = repo.index.diff("HEAD", create_patch=True)
            diff_text = ""
            for d in diffs:
                diff_text += f"--- {d.a_path}\n+++ {d.b_path}\n"
                if d.diff:
                    diff_text += d.diff.decode("utf-8", errors="replace") + "\n"
            return diff_text
        except Exception:
            return ""

    @classmethod
    def get_staged_files(cls, repo_path: Optional[Path] = None) -> List[str]:
        repo = cls.get_repo(repo_path)
        if not repo:
            return []
        try:
            diffs = repo.index.diff("HEAD")
            return [d.a_path or d.b_path for d in diffs if d.a_path or d.b_path]
        except Exception:
            return []
