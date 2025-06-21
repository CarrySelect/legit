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
