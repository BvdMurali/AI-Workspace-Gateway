"""
AI Workspace Gateway - Repository Discovery
Implements local Git repository discovery by reading file structures directly.
"""

import asyncio
import configparser
import os
from typing import Any, Dict, List, Optional

# Standard ignored directories to optimize search performance and avoid deep traversals
IGNORED_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
    ".pytest_cache",
    "__pycache__",
    ".gateway",
    ".gateway-dev"
}


class RepositoryDiscoveryService:
    """Discovers Git repositories on the local filesystem without spawning Git processes."""

    def _parse_git_repo(self, repo_path: str) -> Optional[Dict[str, Any]]:
        """Parses branch and remote URL metadata from local .git files."""
        name = os.path.basename(repo_path)
        
        # Parse Branch
        branch = "unknown"
        head_path = os.path.join(repo_path, ".git", "HEAD")
        if os.path.isfile(head_path):
            try:
                with open(head_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content.startswith("ref:"):
                    branch = content.split("refs/heads/")[-1]
                else:
                    # Detached HEAD, contains commit SHA
                    branch = content[:8]
            except Exception:
                pass

        # Parse Remote URL from config
        remote_url = None
        config_path = os.path.join(repo_path, ".git", "config")
        if os.path.isfile(config_path):
            try:
                config = configparser.ConfigParser()
                config.read(config_path)
                for section in config.sections():
                    if section.startswith('remote "') or section == 'remote':
                        remote_url = config.get(section, 'url', fallback=None)
                        if remote_url:
                            break
            except Exception:
                pass

        return {
            "name": name,
            "root_path": os.path.abspath(repo_path),
            "branch": branch,
            "remote_url": remote_url,
            "status_summary": f"Discovered git repository on branch '{branch}'."
        }

    def discover_repositories(self, root_dir: str, max_depth: int = 3) -> List[Dict[str, Any]]:
        """Synchronously scans folders up to max_depth for Git repositories."""
        repos = []
        root_path = os.path.abspath(root_dir)
        
        if not os.path.exists(root_path) or not os.path.isdir(root_path):
            return repos

        # If the root itself is a git repo
        if os.path.isdir(os.path.join(root_path, ".git")):
            repo_info = self._parse_git_repo(root_path)
            if repo_info:
                repos.append(repo_info)
            return repos

        root_depth = root_path.count(os.sep)
        for root, dirs, _ in os.walk(root_path, followlinks=False):
            # Calculate current depth relative to root_path
            current_depth = root.count(os.sep) - root_depth
            if current_depth >= max_depth:
                dirs[:] = []  # stop descending
                continue

            if ".git" in dirs:
                repo_info = self._parse_git_repo(root)
                if repo_info:
                    repos.append(repo_info)
                # Once we find a git repo, we don't need to walk inside it
                dirs[:] = []
            else:
                # Prune ignored directories in-place to prevent os.walk from entering them
                dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]

        return repos

    async def discover_repositories_async(self, root_dir: str, max_depth: int = 3) -> List[Dict[str, Any]]:
        """Asynchronously discovers Git repositories by running file operations in a threadpool."""
        return await asyncio.to_thread(self.discover_repositories, root_dir, max_depth)
