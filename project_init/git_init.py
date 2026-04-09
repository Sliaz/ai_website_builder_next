"""
git_init.py

Initializes a Git repository for the generated project and pushes it
to a new GitHub repository under the authenticated user's account.

Supports both initialization methods:
  - CLI method  (npm create sanity) → project lives at OUTPUT_DIR
  - Degit method (npx degit)        → project lives at OUTPUT_DIR

In both cases OUTPUT_DIR is passed in as `project_path`.

Authentication strategy (in order of preference):
  1. GitHub CLI (`gh`) — if installed and already logged in, zero friction.
     If installed but not logged in, we run `gh auth login` interactively.
  2. Personal Access Token — fallback when `gh` is not installed.
     The token needs the `repo` scope.
"""

import os
import subprocess
import sys
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _run(cmd: list[str], cwd: str | Path, capture: bool = False) -> subprocess.CompletedProcess:
    """Run a shell command, optionally capturing output."""
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        check=True,
        capture_output=capture,
        text=capture,
    )


def _run_safe(cmd: list[str], cwd: str | Path = ".") -> subprocess.CompletedProcess | None:
    """Run a command and return None on failure instead of raising."""
    try:
        return subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return None


def _gh_available() -> bool:
    """Return True if the GitHub CLI is installed."""
    result = _run_safe(["gh", "--version"])
    return result is not None and result.returncode == 0


def _gh_logged_in() -> bool:
    """Return True if `gh` already has an active authenticated session."""
    result = _run_safe(["gh", "auth", "status"])
    return result is not None and result.returncode == 0


def _get_gh_username() -> str | None:
    """Return the GitHub username of the currently logged-in gh user."""
    result = _run_safe(["gh", "api", "user", "--jq", ".login"])
    if result and result.returncode == 0:
        return result.stdout.strip()
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Git local initialisation
# ─────────────────────────────────────────────────────────────────────────────

def init_local_git(project_path: Path, commit_message: str = "Initial commit") -> bool:
    """
    Run `git init`, stage everything and create the first commit.
    Safe to call even if .git already exists (git init is idempotent).

    Returns True on success, False on failure.
    """
    try:
        # Check if already a git repo
        existing = _run_safe(["git", "rev-parse", "--is-inside-work-tree"], cwd=project_path)
        already_repo = existing is not None and existing.returncode == 0

        if not already_repo:
            print("  → Running git init...")
            _run(["git", "init"], cwd=project_path)
        else:
            print("  → Git repository already initialised, skipping git init.")

        # Stage all files
        print("  → Staging all files...")
        _run(["git", "add", "."], cwd=project_path)

        # Check if there's anything to commit
        status = _run_safe(["git", "status", "--porcelain"], cwd=project_path)
        if status and status.stdout.strip() == "":
            print("  → Nothing to commit, working tree clean.")
        else:
            print(f"  → Creating initial commit: \"{commit_message}\"")
            _run(["git", "commit", "-m", commit_message], cwd=project_path)

        return True

    except subprocess.CalledProcessError as e:
        print(f"\n✗ Git local initialisation failed: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# GitHub authentication
# ─────────────────────────────────────────────────────────────────────────────

def authenticate_github() -> dict | None:
    """
    Ensure the user is authenticated with GitHub.

    Returns a dict with:
        {
            "method": "gh" | "token",
            "token": str | None,   # only set for token method
            "username": str | None
        }

    Returns None if authentication fails or the user cancels.
    """
    print("\n=== GitHub Authentication ===")

    if _gh_available():
        print("✓ GitHub CLI (gh) detected.")

        if _gh_logged_in():
            username = _get_gh_username()
            print(f"✓ Already logged in as: {username or 'unknown'}")
            return {"method": "gh", "token": None, "username": username}

        print("\nYou are not logged into the GitHub CLI.")
        choice = input("Would you like to login now with `gh auth login`? (y/n): ").strip().lower()

        if choice == "y":
            try:
                # Interactive login — gh handles browser / SSH / token flows
                subprocess.run(["gh", "auth", "login"], check=True)
                username = _get_gh_username()
                print(f"\n✓ Logged in as: {username or 'unknown'}")
                return {"method": "gh", "token": None, "username": username}
            except subprocess.CalledProcessError:
                print("✗ Login failed.")
                return None
        else:
            print("Skipping GitHub CLI login.")
            # Fall through to token method below

    else:
        print("⚠️  GitHub CLI (gh) is not installed.")
        print("   You can install it from: https://cli.github.com/")
        print("   Falling back to Personal Access Token authentication.\n")

    # ── Token fallback ────────────────────────────────────────────────────────
    print("You will need a GitHub Personal Access Token with the 'repo' scope.")
    print("Create one at: https://github.com/settings/tokens/new")
    print("  → Select scopes: repo (full control of private repositories)\n")

    token = input("Enter your GitHub Personal Access Token: ").strip()
    if not token:
        print("✗ No token provided. Skipping GitHub setup.")
        return None

    # Verify the token by calling /user
    import urllib.request
    import urllib.error
    import json as _json

    req = urllib.request.Request(
        "https://api.github.com/user",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            user_data = _json.loads(resp.read().decode())
            username = user_data.get("login", "unknown")
            print(f"✓ Token verified. Logged in as: {username}")
            return {"method": "token", "token": token, "username": username}
    except urllib.error.HTTPError as e:
        print(f"✗ Token verification failed (HTTP {e.code}). Check the token and try again.")
        return None
    except Exception as e:
        print(f"✗ Could not verify token: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# GitHub repository creation
# ─────────────────────────────────────────────────────────────────────────────

def _create_repo_gh(repo_name: str, description: str, private: bool) -> str | None:
    """
    Create a GitHub repo using the gh CLI and return its remote URL.
    Returns None on failure.
    """
    visibility = "--private" if private else "--public"
    cmd = [
        "gh", "repo", "create",
        repo_name,
        visibility,
        "--description", description,
        "--source", ".",       # use current directory
        "--remote", "origin",
        "--push",              # push immediately
    ]

    try:
        subprocess.run(cmd, check=True)
        # Get the remote URL that gh just set up
        result = _run_safe(["git", "remote", "get-url", "origin"], cwd=".")
        return result.stdout.strip() if result else None
    except subprocess.CalledProcessError as e:
        print(f"✗ gh repo create failed: {e}")
        return None


def _create_repo_token(
    repo_name: str,
    description: str,
    private: bool,
    token: str,
    project_path: Path,
) -> str | None:
    """
    Create a GitHub repo via the REST API using a PAT, add the remote and push.
    Returns the remote URL on success, None on failure.
    """
    import urllib.request
    import urllib.error
    import json as _json

    payload = _json.dumps({
        "name": repo_name,
        "description": description,
        "private": private,
        "auto_init": False,
    }).encode()

    req = urllib.request.Request(
        "https://api.github.com/user/repos",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req) as resp:
            repo_data = _json.loads(resp.read().decode())
            remote_url = repo_data.get("clone_url", "")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"✗ GitHub API error (HTTP {e.code}): {body}")
        return None
    except Exception as e:
        print(f"✗ Failed to create repository: {e}")
        return None

    if not remote_url:
        print("✗ Could not get remote URL from GitHub response.")
        return None

    # Inject the token into the URL so git can authenticate without a prompt
    # https://TOKEN@github.com/user/repo.git
    auth_url = remote_url.replace("https://", f"https://{token}@")

    try:
        # Remove existing origin if any
        existing = _run_safe(["git", "remote", "get-url", "origin"], cwd=project_path)
        if existing and existing.returncode == 0:
            _run(["git", "remote", "remove", "origin"], cwd=project_path)

        _run(["git", "remote", "add", "origin", auth_url], cwd=project_path)
        print(f"  → Pushing to {remote_url} ...")
        _run(["git", "push", "-u", "origin", "HEAD"], cwd=project_path)

        # Replace the authenticated URL with the clean one in .git/config
        # so the token doesn't sit in plain text on disk
        _run(["git", "remote", "set-url", "origin", remote_url], cwd=project_path)

        return remote_url

    except subprocess.CalledProcessError as e:
        print(f"✗ Git push failed: {e}")
        return None


def create_github_repo(
    project_path: Path,
    project_name: str,
    description: str,
    auth_info: dict,
) -> str | None:
    """
    Create a new GitHub repository and push the local project to it.

    Args:
        project_path:  Absolute path to the generated project directory.
        project_name:  Suggested repository name (user can override).
        description:   Short description for the GitHub repo.
        auth_info:     Dict returned by authenticate_github().

    Returns:
        The repository URL on success, None on failure.
    """
    print("\n=== Create GitHub Repository ===")

    # Let the user customise the repo name
    suggested = project_name.lower().replace(" ", "-")
    repo_name_input = input(f"Repository name (default: {suggested}): ").strip()
    repo_name = repo_name_input if repo_name_input else suggested

    # Public or private?
    visibility_input = input("Make repository private? (y/n, default: y): ").strip().lower()
    private = visibility_input != "n"

    print(f"\n  Creating {'private' if private else 'public'} repository: {repo_name}")

    if auth_info["method"] == "gh":
        # gh handles both creation and push in one command
        remote_url = _create_repo_gh(repo_name, description, private)
    else:
        remote_url = _create_repo_token(
            repo_name=repo_name,
            description=description,
            private=private,
            token=auth_info["token"],
            project_path=project_path,
        )

    if remote_url:
        print(f"\n✓ Repository created and pushed successfully!")
        print(f"  URL: {remote_url}")
    else:
        print("\n✗ Repository creation failed.")
        print("  You can create it manually:")
        print("    1. Go to https://github.com/new")
        print(f"   2. Create a repository named '{repo_name}'")
        print(f"   3. Run: cd {project_path}")
        print( "      git remote add origin <your-repo-url>")
        print( "      git push -u origin HEAD")

    return remote_url


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point — call this from project_init/main.py
# ─────────────────────────────────────────────────────────────────────────────

def setup_github_repository(project_path: str | Path, project_name: str, description: str = "") -> str | None:
    """
    Full GitHub setup flow:
      1. Initialise a local git repo and make the first commit.
      2. Authenticate with GitHub (gh CLI or PAT).
      3. Create a remote repository and push.

    This function is designed to be called at the end of both
    `init_project()` and `init_project_degit()` in project_init/main.py.

    Args:
        project_path:  Path to the generated project on disk.
        project_name:  Name of the project (used as suggested repo name).
        description:   Short description for the GitHub repo (optional).

    Returns:
        The GitHub repository URL on success, None if the user skips or
        an error occurs.
    """
    project_path = Path(project_path)

    if not project_path.exists():
        print(f"✗ Project path does not exist: {project_path}")
        return None

    print("\n" + "=" * 60)
    print("   GitHub Repository Setup")
    print("=" * 60)

    # Ask if user wants to set up GitHub at all
    choice = input("\nWould you like to push this project to GitHub? (y/n): ").strip().lower()
    if choice != "y":
        print("Skipping GitHub setup.")
        print(f"\nTo set it up later, run from {project_path}:")
        print("  git init && git add . && git commit -m 'Initial commit'")
        print("  gh repo create   (or create a repo at github.com/new and git remote add origin <url>)")
        return None

    # Step 1: Local git init + first commit
    print("\n--- Step 1: Local Git Initialisation ---")
    success = init_local_git(project_path)
    if not success:
        print("✗ Could not initialise local git repository. Skipping GitHub setup.")
        return None

    # Step 2: Authenticate
    print("\n--- Step 2: GitHub Authentication ---")
    auth_info = authenticate_github()
    if auth_info is None:
        print("✗ Authentication failed or cancelled. Skipping GitHub setup.")
        print(f"\nYour local git repo is ready at: {project_path}")
        print("Push it manually when you have GitHub credentials.")
        return None

    # Step 3: Create remote repo + push
    print("\n--- Step 3: Create Remote Repository ---")
    repo_url = create_github_repo(
        project_path=project_path,
        project_name=project_name,
        description=description or f"Generated project: {project_name}",
        auth_info=auth_info,
    )

    print("\n" + "=" * 60)
    return repo_url