import textwrap

import pytest
from io import StringIO

from legit.command import Command
from legit.repository import Repository

from tests.cmd_helper import (
    assert_stdout,
    repo,
    make_executable,
    make_unreadable,
    repo_path,
    write_file,
    commit,
    legit_cmd,
    mkdir,
    committed_repo,
)


def assert_status(legit_cmd, output):
    cmd, stdin, stdout, stderr = legit_cmd("status")
    assert_stdout(stdout, output)


def test_list_untracked_files_in_name_order(write_file, legit_cmd):
    write_file("file.txt", "")
    write_file("another.txt", "")
    
    expected = textwrap.dedent(
        """\
        ?? another.txt
        ?? file.txt
        """
    )

    assert_status(legit_cmd, expected)


def test_lists_files_as_untracked_if_they_are_not_in_the_index(write_file, commit, legit_cmd):
    write_file("committed.txt", "")
    legit_cmd("add", ".")
    commit("commit message")

    write_file("file.txt", "")

    expected = textwrap.dedent(
        """\
        ?? file.txt
        """
    )

    assert_status(legit_cmd, expected)


def test_lists_untracked_directories_and_not_their_contents(write_file, legit_cmd):
    write_file("file.txt", "")
    write_file("dir/another.txt", "")

    expected = textwrap.dedent(
        """\
        ?? dir/
        ?? file.txt
        """
    )

    assert_status(legit_cmd, expected)


def test_lists_untracked_files_inside_tracked_directories(write_file, commit, legit_cmd):
    write_file("a/b/inner.txt", "")
    legit_cmd("add", ".")
    commit("commit message")

    write_file("a/outer.txt", "")
    write_file("a/b/c/file.txt", "")

    expected = textwrap.dedent(
        """\
        ?? a/b/c/
        ?? a/outer.txt
        """
    )

    assert_status(legit_cmd, expected)


def test_does_not_list_empty_untracked_directories(mkdir, legit_cmd):
    mkdir("outer")
    expected = ""
    
    assert_status(legit_cmd, expected)


def test_lists_untracked_directories_that_indirectly_contain_files(write_file, legit_cmd):
    write_file("outer/inner/file.txt", "")

    expected = textwrap.dedent(
        """\
        ?? outer/
        """
    )

    assert_status(legit_cmd, expected)


@pytest.mark.usefixtures("committed_repo")
class TestIndexWorkspaceChanges:
    def test_no_changes_prints_nothing(self, legit_cmd):
        assert_status(legit_cmd, "")

    def test_reports_modified_files(self, write_file, legit_cmd):
        write_file("1.txt", "changed")
        write_file("a/2.txt", "modified")
        assert_status(legit_cmd, " M 1.txt\n M a/2.txt\n")

