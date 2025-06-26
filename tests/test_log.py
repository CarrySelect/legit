import textwrap
import pytest
from tests.conftest import assert_stdout


@pytest.fixture
def commit_file(write_file, legit_cmd, commit):
    def _commit_file(msg, time=None):
        write_file("file.txt", msg)
        legit_cmd("add", ".")
        commit(msg, time)
    return _commit_file


@pytest.fixture
def commit_tree(write_file, legit_cmd, commit):
    def _commit_tree(msg, files):
        for path, contents in files.items():
            write_file(path, contents)
        legit_cmd("add", ".")
        commit(msg)
    return _commit_tree


@pytest.fixture(autouse=True)
def chain_of_commits(commit_file, legit_cmd, load_commit):
    # now we can use commit_file as a real fixture
    msgs = ["A", "B", "C"]
    for msg in msgs:
        commit_file(msg)
    legit_cmd("branch", "topic", "@^^")
    commits = [load_commit(rev) for rev in ["@", "@^", "@^^"]]
    return commits


def test_prints_a_log_in_medium_format(legit_cmd, chain_of_commits):
    commits = chain_of_commits

    cmd, stdin, stdout, stderr = legit_cmd("log")

    expected_log = textwrap.dedent(f"""\
        commit {commits[0].oid}
        Author: A. U. Thor <author@example.com>
        Date:   {commits[0].author.readable_time()}

            {commits[0].message}

        commit {commits[1].oid}
        Author: A. U. Thor <author@example.com>
        Date:   {commits[1].author.readable_time()}

            {commits[1].message}

        commit {commits[2].oid}
        Author: A. U. Thor <author@example.com>
        Date:   {commits[2].author.readable_time()}

            {commits[2].message}

    """)

    assert_stdout(stdout, expected_log.strip())

