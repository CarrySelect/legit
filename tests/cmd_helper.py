import shutil
import pytest
from pathlib import Path
from io import StringIO

from legit.repository import Repository
from legit.command import Command

@pytest.fixture
def repo_path(tmp_path):
    """
    Create a fresh test repository path under pytest's tmp_path.
    """
    return tmp_path / "test_repo"

@pytest.fixture(autouse=True)
def setup_and_teardown(repo_path):
    """
    Initialize a repository before each test and clean up afterward.
    """
    # initialize repository (e.g., `init` command)
    Command.execute(repo_path, {}, ["init"], StringIO(), StringIO(), StringIO())
    yield
    # teardown: remove the repo directory
    shutil.rmtree(repo_path, ignore_errors=True)

@pytest.fixture
def repo(repo_path):
    """
    Provide a Repository instance pointed at the .git directory.
    """
    git_dir = repo_path / ".git"
    return Repository(git_dir)

@pytest.fixture
def write_file(repo_path):
    """
    Write `contents` to `repo_path/name`, creating parent dirs as needed.
    """
    def _write_file(name: str, contents: str):
        path = repo_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            f.write(contents)
    return _write_file

@pytest.fixture
def make_executable(repo_path):
    """
    Make the file at `repo_path/name` executable (0755).
    """
    def _make_executable(name: str):
        path = repo_path / name
        path.chmod(0o755)
    return _make_executable

@pytest.fixture
def make_unreadable(repo_path):
    """
    Make the file at `repo_path/name` unreadable (0200).
    """
    def _make_unreadable(name: str):
        path = repo_path / name
        path.chmod(0o200)
    return _make_unreadable

@pytest.fixture
def legit_cmd(repo_path):
    """
    Run the command with StringIO streams and return (cmd, stdin, stdout, stderr).
    """
    def _legit_cmd(*argv):
        stdin = StringIO()
        stdout = StringIO()
        stderr = StringIO()
        cmd = Command.execute(repo_path, {}, [""] + list(argv), stdin, stdout, stderr)
        return cmd, stdin, stdout, stderr
    return _legit_cmd

# Helper assertion functions (optional; you can also assert inline in tests)
def assert_status(cmd, expected):
    assert cmd.status == expected, f"Expected status {expected}, got {cmd.status}"

def assert_stdout(stdout, expected):
    stdout.seek(0)
    data = stdout.read()
    assert data == expected, f"Expected stdout {expected!r}, got {data!r}"

def assert_stderr(stderr, expected):
    stderr.seek(0)
    data = stderr.read()
    assert data == expected, f"Expected stderr {expected!r}, got {data!r}"

