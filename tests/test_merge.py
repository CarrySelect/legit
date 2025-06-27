import pytest
from pathlib import Path
from tests.conftest import assert_stdout


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
    """Commit *files* under *msg* the same way the Ruby helper did."""
    def _commit_tree(msg: str, files: dict[str, str]):
        for path, contents in files.items():
            write_file(path, contents)
        legit_cmd("add", ".")
        commit(msg)
    return _commit_tree


class TestUnconflictedMergeWithTwoFiles:
    @pytest.fixture(autouse=True)
    def setup(self, commit_tree, legit_cmd):
        # root commit with both files
        commit_tree(
            "root",
            {
                "f.txt": "1",
                "g.txt": "1",
            },
        )

        # topic branch modifies g.txt
        legit_cmd("branch", "topic")
        legit_cmd("checkout", "topic")
        commit_tree(
            "right",
            {
                "g.txt": "2",
            },
        )

        # master modifies f.txt
        legit_cmd("checkout", "master")
        commit_tree(
            "left",
            {
                "f.txt": "2",
            },
        )

        # perform the merge (supply a merge message on stdin)
        legit_cmd("merge", "topic", stdin_data="merge topic branch")

    # ---------------------------------------------------------------------
    def test_puts_the_combined_changes_in_the_workspace(self, repo_path):
        assert_workspace(
            repo_path,
            {
                "f.txt": "2",
                "g.txt": "2",
            },
        )

    def test_leaves_the_status_clean(self, legit_cmd):
        cmd, stdin, stdout, stderr = legit_cmd("status", "--porcelain")
        assert_stdout(stdout, "")

    def test_writes_a_commit_with_correct_parents(self, load_commit):
        commit     = load_commit("@")     # HEAD
        old_head   = load_commit("@^")    # first parent
        merge_head = load_commit("topic") # second parent

        assert commit.parents == [old_head.oid, merge_head.oid]


class TestMultipleCommonAncestors:
    @pytest.fixture(autouse=True)
    def setup_repo(self, commit_tree, legit_cmd):
        # Commits on master: A, B, C
        commit_tree("A", {"f.txt": "1"})
        commit_tree("B", {"f.txt": "2"})
        commit_tree("C", {"f.txt": "3"})

        # topic branch off master^  (points to B)
        legit_cmd("branch", "topic", "master^")
        legit_cmd("checkout", "topic")
        commit_tree("D", {"g.txt": "1"})
        commit_tree("E", {"g.txt": "2"})
        commit_tree("F", {"g.txt": "3"})

        # joiner branch off topic^ (points to E)
        legit_cmd("branch", "joiner", "topic^")
        legit_cmd("checkout", "joiner")
        commit_tree("G", {"h.txt": "1"})

        # back to master for the actual tests
        legit_cmd("checkout", "master")

    # ---------------------------------------------------------------------
    def test_performs_the_first_merge(self, repo_path, legit_cmd):
        cmd, _, _, _ = legit_cmd("merge", "joiner", stdin_data="merge joiner")
        assert cmd.status == 0 

        assert_workspace(
            repo_path,
            {
                "f.txt": "3",
                "g.txt": "2",
                "h.txt": "1",
            },
        )

        cmd, stdin, stdout, stderr = legit_cmd("status", "--porcelain")
        assert_stdout(stdout, "")

    # ---------------------------------------------------------------------
    def test_performs_the_second_merge(self, repo_path, legit_cmd, commit_tree):
        # First merge (same as previous test)
        legit_cmd("merge", "joiner", stdin_data="merge joiner")

        # New commit H on master
        commit_tree("H", {"f.txt": "4"})

        # Second merge, bringing in topic
        cmd, _, _, _ = legit_cmd("merge", "topic", stdin_data="merge topic")
        assert cmd.status == 0

        assert_workspace(
            repo_path,
            {
                "f.txt": "4",
                "g.txt": "3",
                "h.txt": "1",
            },
        )

        cmd, stdin, stdout, stderr = legit_cmd("status", "--porcelain")
        assert_stdout(stdout, "")



