import subprocess
from pathlib import Path


def run(cmd: list[str], cwd: Path | str) -> subprocess.CompletedProcess:
    result = subprocess.run(cmd, cwd=cwd, check=True)
    return result


def run_capture(cmd: list[str], cwd: Path | str = ".") -> subprocess.CompletedProcess:
    """Run command and capture output (doesn't raise on error)."""
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result
