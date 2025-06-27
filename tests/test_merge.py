import pytest
from pathlib import Path


def _snapshot_workspace(repo_path: Path) -> dict[str, str]:
    """Return a {relative_path: contents} mapping for every *file* in the repo.

    The `.git` directory is purposely ignored.
    """
    result: dict[str, str] = {}
    for path in repo_path.rglob("*"):
        if ".git" in path.parts or not path.is_file():
            continue
        result[path.relative_to(repo_path).as_posix()] = path.read_text()
    return result


def assert_workspace(repo_path: Path, expected: dict[str, str]):
    """Assert that the working directory exactly matches *expected*."""
    actual = _snapshot_workspace(repo_path)
    assert actual == expected, f"workspace mismatch – expected {expected}, got {actual}"



@pytest.fixture
def commit_tree(write_file, legit_cmd, commit):
    def _commit_tree(msg, files):
        for path, contents in files.items():
            write_file(path, contents)
        legit_cmd("add", ".")
        commit(msg)
    return _commit_tree


class TestUnconflictedMergeWithTwoFiles:
    @pytest.fixture(autouse=True)
    def setup(self, commit_tree, legit_cmd):
        commit_tree("root", {
            "f.txt": "1",
            "g.txt": "1",
        })
        
        legit_cmd("branch", "topic")
        legit_cmd("checkout", "topic")
        commit_tree("right", {
            "g.txt": "2"
        })

        legit_cmd("checkout", "master")
        commit_tree("left", {
            "f.txt": "2"
        })

        legit_cmd("merge", "topic", stdin_data="merge branch topic")

    def test_puts_the_combined_changes_in_the_workspace(self, repo_path):
        assert_workspace(repo_path, {
            "f.txt": "2",
            "g.txt": "2",
        })

