import enum
import textwrap
from pathlib import Path

import pytest

from tests.conftest import assert_stdout


class FileMode(enum.Enum):
    EXECUTABLE = enum.auto()


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
def commit_tree(write_file, legit_cmd, commit, delete, make_executable):
    def _commit_tree(msg: str, files: dict[str, str]):
        for path, contents in files.items():
            if contents != FileMode.EXECUTABLE:
                delete(path)

            if contents == FileMode.EXECUTABLE:
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


class TestFastForwardMerge:
    @pytest.fixture(autouse=True)
    def setup(self, commit_tree, legit_cmd):
        commit_tree("A", {"f.txt": "1"})
        commit_tree("B", {"f.txt": "2"})
        commit_tree("C", {"f.txt": "3"})

        legit_cmd("branch", "topic", "@^^")
        legit_cmd("checkout", "topic")

        self.cmd, self.stdin, self.stdout, self.stderr = legit_cmd("merge", "master", stdin_data="M")

    def test_it_prints_the_fast_forward_message(self, repo, resolve_revision):
        a, b = map(resolve_revision, ["master^^", "master"])
        expected = textwrap.dedent(
            f"""\
            Updating {repo.database.short_oid(a)}..{repo.database.short_oid(b)}
            Fast-forward
            """
        )
        assert_stdout(self.stdout, expected)
    
    def test_it_updates_the_current_branch_head(self, load_commit, legit_cmd):
        commit = load_commit("@")
        assert commit.message == "C"

        cmd, stdin, stdout, stderr = legit_cmd("status", "--porcelain")
        assert_stdout(stdout, "")


class TestUnconflictedMergeWithTwoFiles:
    @pytest.fixture(autouse=True)
    def setup(self, merge3):
        merge3(
            {"f.txt": "1", "g.txt": "1"},
            {"f.txt": "2",             },
            {              "g.txt": "2"},
        )

    def test_it_puts_the_combined_changes_in_the_workspace(self, repo_path):
        assert_workspace(repo_path, {
            "f.txt": "2",
            "g.txt": "2",
        })

    def test_it_creates_a_clean_merge(self, legit_cmd, load_commit,):
        assert_clean_merge(legit_cmd, load_commit)


@pytest.fixture
def assert_executable(repo_path):
    """Assert that a file in the workspace has the executable bit set."""

    def _assert_executable(path: str | Path):
        full = (repo_path / path).resolve()
        mode = full.stat().st_mode
        assert mode & 0o111, f"{path} is not executable"

    return _assert_executable


class TestUnconflictedMergeWithDeletedFile:
    @pytest.fixture(autouse=True)
    def setup(self, merge3):
        merge3(
            {"f.txt": "1", "g.txt": "1"},
            {"f.txt": "2"},
            {"g.txt": None},
        )

    def test_it_puts_the_combined_changes_in_the_workspace(self, repo_path):
        assert_workspace(repo_path, {
            "f.txt": "2",
        })

    def test_it_creates_a_clean_merge(self, legit_cmd, load_commit):
        assert_clean_merge(legit_cmd, load_commit)


class TestUnconflictedMergeSameAdditionOnBothSides:
    @pytest.fixture(autouse=True)
    def setup(self, merge3):
        merge3(
            {"f.txt": "1"},
            {"g.txt": "2"},
            {"g.txt": "2"},
        )

    def test_it_puts_the_combined_changes_in_the_workspace(self, repo_path):
        assert_workspace(repo_path, {
            "f.txt": "1",
            "g.txt": "2",
        })

    def test_it_creates_a_clean_merge(self, legit_cmd, load_commit):
        assert_clean_merge(legit_cmd, load_commit)


class TestUnconflictedMergeSameEditOnBothSides:
    @pytest.fixture(autouse=True)
    def setup(self, merge3):
        merge3(
            {"f.txt": "1"},
            {"f.txt": "2"},
            {"f.txt": "2"},
        )

    def test_it_puts_the_combined_changes_in_the_workspace(self, repo_path):
        assert_workspace(repo_path, {"f.txt": "2"})

    def test_it_creates_a_clean_merge(self, legit_cmd, load_commit):
        assert_clean_merge(legit_cmd, load_commit)


class TestUnconflictedMergeEditAndModeChange:
    @pytest.fixture(autouse=True)
    def setup(self, merge3):
        merge3(
            {"f.txt": "1"},
            {"f.txt": "2"},
            {"f.txt": FileMode.EXECUTABLE},
        )

    def test_it_puts_the_combined_changes_in_the_workspace(self, repo_path, assert_executable):
        assert_workspace(repo_path, {"f.txt": "2"})
        assert_executable("f.txt")

    def test_it_creates_a_clean_merge(self, legit_cmd, load_commit):
        assert_clean_merge(legit_cmd, load_commit)


class TestUnconflictedMergeModeChangeAndEdit:
    @pytest.fixture(autouse=True)
    def setup(self, merge3):
        merge3(
            {"f.txt": "1"},
            {"f.txt": FileMode.EXECUTABLE},
            {"f.txt": "3"},
        )

    def test_it_puts_the_combined_changes_in_the_workspace(self, repo_path, assert_executable):
        assert_workspace(repo_path, {"f.txt": "3"})
        assert_executable("f.txt")

    def test_it_creates_a_clean_merge(self, legit_cmd, load_commit):
        assert_clean_merge(legit_cmd, load_commit)


class TestUnconflictedMergeSameDeletionOnBothSides:
    @pytest.fixture(autouse=True)
    def setup(self, merge3):
        merge3(
            {"f.txt": "1", "g.txt": "1"},
            {"g.txt": None},
            {"g.txt": None},
        )

    def test_it_puts_the_combined_changes_in_the_workspace(self, repo_path):
        assert_workspace(repo_path, {"f.txt": "1"})

    def test_it_creates_a_clean_merge(self, legit_cmd, load_commit):
        assert_clean_merge(legit_cmd, load_commit)


class TestUnconflictedMergeDeleteAddParent:
    @pytest.fixture(autouse=True)
    def setup(self, merge3):
        merge3(
            {"nest/f.txt": "1"},
            {"nest/f.txt": None},
            {"nest": "3"},
        )

    def test_it_puts_the_combined_changes_in_the_workspace(self, repo_path):
        assert_workspace(repo_path, {"nest": "3"})

    def test_it_creates_a_clean_merge(self, legit_cmd, load_commit):
        assert_clean_merge(legit_cmd, load_commit)


class TestUnconflictedMergeDeleteAddChild:
    @pytest.fixture(autouse=True)
    def setup(self, merge3):
        merge3(
            {"nest/f.txt": "1"},
            {"nest/f.txt": None},
            {"nest/f.txt": None, "nest/f.txt/g.txt": "3"},
        )

    def test_it_puts_the_combined_changes_in_the_workspace(self, repo_path):
        assert_workspace(repo_path, {"nest/f.txt/g.txt": "3"})

    def test_it_creates_a_clean_merge(self, legit_cmd, load_commit):
        assert_clean_merge(legit_cmd, load_commit)


class TestConflictedMergeAddAdd:
    @pytest.fixture(autouse=True)
    def setup(self, merge3):
        merge3(
            {"f.txt": "1"},
            {"g.txt": "2"},
            {"g.txt": ["2"]},
        )

    def test_it_puts_the_conflicted_file_in_the_workspace(self, repo_path):
        assert_workspace(repo_path, {
            "f.txt": "1",
            "g.txt": "2",
        })

    def test_it_records_the_conflict_in_the_index(self, repo):
        assert_index(repo,
            ("f.txt", 0),
            ("g.txt", 2),
            ("g.txt", 3),
        )

    def test_it_does_not_write_a_merge_commit(self, legit_cmd, load_commit):
        assert_no_merge(legit_cmd, load_commit)


class TestConflictedMergeFileDirectoryAddition:
    @pytest.fixture(autouse=True)
    def setup(self, merge3):
        merge3(
            {"f.txt": "1"},
            {"g.txt": "2"},
            {"g.txt/nested.txt": "3"},
        )

    def test_it_puts_a_namespaced_copy_in_the_workspace(self, repo_path):
        assert_workspace(repo_path, {
            "f.txt": "1",
            "g.txt~HEAD": "2",
            "g.txt/nested.txt": "3",
        })

    def test_it_records_the_conflict_in_the_index(self, repo):
        assert_index(repo,
            ("f.txt", 0),
            ("g.txt", 2),
            ("g.txt/nested.txt", 0),
        )

    def test_it_does_not_write_a_merge_commit(self, legit_cmd, load_commit):
        assert_no_merge(legit_cmd, load_commit)


class TestConflictedMergeDirectoryFileAddition:
    @pytest.fixture(autouse=True)
    def setup(self, merge3):
        merge3(
            {"f.txt": "1"},
            {"g.txt/nested.txt": "2"},
            {"g.txt": "3"},
        )

    def test_it_puts_a_namespaced_copy_in_the_workspace(self, repo_path):
        assert_workspace(repo_path, {
            "f.txt": "1",
            "g.txt~topic": "3",
            "g.txt/nested.txt": "2",
        })

    def test_it_records_the_conflict_in_the_index(self, repo):
        assert_index(repo,
            ("f.txt", 0),
            ("g.txt", 3),
            ("g.txt/nested.txt", 0),
        )

    def test_it_does_not_write_a_merge_commit(self, legit_cmd, load_commit):
        assert_no_merge(legit_cmd, load_commit)


class TestConflictedMergeEditEdit:
    @pytest.fixture(autouse=True)
    def setup(self, merge3):
        merge3(
            {"f.txt": "1\n"},
            {"f.txt": "2\n"},
            {"f.txt": "3\n"},
        )

    def test_it_puts_the_conflicted_file_in_the_workspace(self, repo_path):
        assert_workspace(repo_path, {
            "f.txt": "<<<<<<< HEAD\n2\n=======\n3\n>>>>>>> topic\n",
        })

    def test_it_records_the_conflict_in_the_index(self, repo):
        assert_index(repo,
            ("f.txt", 1),
            ("f.txt", 2),
            ("f.txt", 3),
        )

    def test_it_does_not_write_a_merge_commit(self, legit_cmd, load_commit):
        assert_no_merge(legit_cmd, load_commit)


class TestConflictedMergeEditDelete:
    @pytest.fixture(autouse=True)
    def setup(self, merge3):
        merge3(
            {"f.txt": "1"},
            {"f.txt": "2"},
            {"f.txt": None},
        )

    def test_it_puts_the_left_version_in_the_workspace(self, repo_path):
        assert_workspace(repo_path, {"f.txt": "2"})

    def test_it_records_the_conflict_in_the_index(self, repo):
        assert_index(repo,
            ("f.txt", 1),
            ("f.txt", 2),
        )

    def test_it_does_not_write_a_merge_commit(self, legit_cmd, load_commit):
        assert_no_merge(legit_cmd, load_commit)


class TestConflictedMergeDeleteEdit:
    @pytest.fixture(autouse=True)
    def setup(self, merge3):
        merge3(
            {"f.txt": "1"},
            {"f.txt": None},
            {"f.txt": "3"},
        )

    def test_it_puts_the_right_version_in_the_workspace(self, repo_path):
        assert_workspace(repo_path, {"f.txt": "3"})

    def test_it_records_the_conflict_in_the_index(self, repo):
        assert_index(repo,
            ("f.txt", 1),
            ("f.txt", 3),
        )

    def test_it_does_not_write_a_merge_commit(self, legit_cmd, load_commit):
        assert_no_merge(legit_cmd, load_commit)


class TestConflictedMergeEditAddParent:
    @pytest.fixture(autouse=True)
    def setup(self, merge3):
        merge3(
            {"nest/f.txt": "1"},
            {"nest/f.txt": "2"},
            {"nest": "3"},
        )

    def test_it_puts_a_namespaced_copy_in_the_workspace(self, repo_path):
        assert_workspace(repo_path, {
            "nest/f.txt": "2",
            "nest~topic": "3",
        })

    def test_it_records_the_conflict_in_the_index(self, repo):
        assert_index(repo,
            ("nest", 3),
            ("nest/f.txt", 1),
            ("nest/f.txt", 2),
        )

    def test_it_does_not_write_a_merge_commit(self, legit_cmd, load_commit):
        assert_no_merge(legit_cmd, load_commit)


class TestConflictedMergeEditAddChild:
    @pytest.fixture(autouse=True)
    def setup(self, merge3):
        merge3(
            {"nest/f.txt": "1"},
            {"nest/f.txt": "2"},
            {"nest/f.txt": None, "nest/f.txt/g.txt": "3"},
        )

    def test_it_puts_a_namespaced_copy_in_the_workspace(self, repo_path):
        assert_workspace(repo_path, {
            "nest/f.txt~HEAD": "2",
            "nest/f.txt/g.txt": "3",
        })

    def test_it_records_the_conflict_in_the_index(self, repo):
        assert_index(repo,
            ("nest/f.txt", 1),  # missing
            ("nest/f.txt", 2),
            ("nest/f.txt/g.txt", 0),
        )

    def test_it_does_not_write_a_merge_commit(self, legit_cmd, load_commit):
        assert_no_merge(legit_cmd, load_commit)


class TestMultipleCommonAncestors:
    @pytest.fixture(autouse=True)
    def setup(self, commit_tree, legit_cmd):
        # Build the commit graph out as described in the original Ruby spec.
        commit_tree("A", {"f.txt": "1"})
        commit_tree("B", {"f.txt": "2"})
        commit_tree("C", {"f.txt": "3"})

        legit_cmd("branch", "topic", "master^")
        legit_cmd("checkout", "topic")
        commit_tree("D", {"g.txt": "1"})
        commit_tree("E", {"g.txt": "2"})
        commit_tree("F", {"g.txt": "3"})

        legit_cmd("branch", "joiner", "topic^")
        legit_cmd("checkout", "joiner")
        commit_tree("G", {"h.txt": "1"})

        legit_cmd("checkout", "master")

    def test_it_performs_the_first_merge(self, legit_cmd, repo_path):
        cmd, stdin, stdout, stderr = legit_cmd("merge", "joiner", stdin_data="merge joiner")
        assert cmd.status == 0

        assert_workspace(repo_path, {
            "f.txt": "3",
            "g.txt": "2",
            "h.txt": "1",
        })

        cmd, stdin, stdout, stderr = legit_cmd("status", "--porcelain")
        assert_stdout(stdout, "")

    def test_it_performs_the_second_merge(self, legit_cmd, commit_tree, repo_path):
        legit_cmd("merge", "joiner", stdin_data="merge joiner")

        commit_tree("H", {"f.txt": "4"})
        
        cmd, stdin, stdout, stderr = legit_cmd("merge", "topic", stdin_data="merge topic")
        assert cmd.status == 0

        assert_workspace(repo_path, {
            "f.txt": "4",
            "g.txt": "3",
            "h.txt": "1",
        })

        cmd, stdin, stdout, stderr = legit_cmd("status", "--porcelain")
        assert_stdout(stdout, "")

