import pytest
from pathlib import Path
from tests.conftest import assert_stdout, delete, legit_cmd, load_commit, make_executable


def _snapshot_workspace(repo_path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in repo_path.rglob("*"):
        if ".git" in path.parts or not path.is_file():
            continue
        result[path.relative_to(repo_path).as_posix()] = path.read_text()
    return result


def assert_workspace(repo_path: Path, expected: dict[str, str]):
    actual = _snapshot_workspace(repo_path)
    assert actual == expected, f"workspace mismatch – expected {expected}, got {actual}"


@pytest.fixture
def commit_tree(write_file, legit_cmd, commit, delete):
    def _commit_tree(msg: str, files: dict[str, str]):
        for path, contents in files.items():
            if contents is None:
                make_executable(path)
            elif isinstance(contents, str):
                write_file(path, contents)
            elif isinstance(contents, list):
                write_file(path, contents[0])
                make_executable(path)

        delete(".git/index")
        legit_cmd("add", ".")
        commit(msg)
    
    return _commit_tree


@pytest.fixture
def merge3(commit_tree, legit_cmd):
    def _merge3(base, left, right):
        commit_tree("A", base)
        commit_tree("B", left)

        legit_cmd("branch", "topic", "master^")
        legit_cmd("checkout", "topic")
        commit_tree("C", right)

        legit_cmd("checkout", "master")
        legit_cmd("merge", "topic", stdin_data="M")

    return _merge3

def assert_clean_merge(legit_cmd, load_commit):
    cmd, stdin, stdout, stderr = legit_cmd("status", "--porcelain")
    assert_stdout(stdout, "")

    commit = load_commit("@")
    old_head = load_commit("@^")
    merge_head = load_commit("topic")

    assert commit.message == "M"
    assert commit.parents == [old_head.oid, merge_head.oid]

def assert_no_merge(legit_cmd, load_commit):
    commit = load_commit("@")
    assert commit.message == "B"
    assert len(commit.parents) == 1

def assert_index(repo, *expected_entries):
    repo.index.load()

    actual_entries = [(str(entry.path), entry.stage) for entry in repo.index.entries.values()]

    sorted_actual = sorted(actual_entries)
    sorted_expected = sorted(list(expected_entries))

    assert sorted_actual == sorted_expected, (
        f"Index content mismatch.\n"
        f"  Expected: {sorted_expected}\n"
        f"  Actual:   {sorted_actual}"
    )

class TestMergingAnAncestor:
    @pytest.fixture(autouse=True)
    def setup(self, commit_tree, legit_cmd):
        commit_tree("A", {"f.txt": "1"})
        commit_tree("B", {"f.txt": "2"})
        commit_tree("C", {"f.txt": "3"})

        self.cmd, self.stdin, self.stdout, self.stderr = legit_cmd("merge", "@^")

    def test_it_prints_the_up_to_date_message(self):
        assert_stdout(self.stdout, "Already up to date.\n")

    def test_it_does_not_change_repository_state(self, legit_cmd, load_commit):
        commit = load_commit("@")
        assert commit.message == "C"

        cmd, stdin, stdout, stderr = legit_cmd("status", "--porcelain")
        assert_stdout(stdout, "")


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



