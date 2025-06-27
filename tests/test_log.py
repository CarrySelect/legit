import textwrap
from datetime import datetime, timedelta
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


@pytest.fixture
def chain_of_commits(commit_file, legit_cmd, load_commit):
    # now we can use commit_file as a real fixture
    msgs = ["A", "B", "C"]
    for msg in msgs:
        commit_file(msg)
    legit_cmd("branch", "topic", "@^^")
    commits = [load_commit(rev) for rev in ["@", "@^", "@^^"]]
    return commits



@pytest.mark.usefixtures("chain_of_commits")
class TestWithAChainOfCommits:
    def test_prints_a_log_in_medium_format(self, legit_cmd, chain_of_commits):
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
    
        assert_stdout(stdout, expected_log)
    
    def test_medium_format_with_abbrev_ids(self, legit_cmd, chain_of_commits, repo):
        commits = chain_of_commits
        # run with --abbrev-commit
        _, _, stdout, _ = legit_cmd("log", "--abbrev-commit")
        expected = textwrap.dedent(f"""\
            commit {repo.database.short_oid(commits[0].oid)}
            Author: A. U. Thor <author@example.com>
            Date:   {commits[0].author.readable_time()}
    
                C
    
            commit {repo.database.short_oid(commits[1].oid)}
            Author: A. U. Thor <author@example.com>
            Date:   {commits[1].author.readable_time()}
    
                B
    
            commit {repo.database.short_oid(commits[2].oid)}
            Author: A. U. Thor <author@example.com>
            Date:   {commits[2].author.readable_time()}
    
                A
        """)
        assert_stdout(stdout, expected)
    
    
    def test_oneline_format(self, legit_cmd, chain_of_commits, repo):
        commits = chain_of_commits
        # run with --oneline (implies abbrev)
        _, _, stdout, _ = legit_cmd("log", "--oneline")
        expected = textwrap.dedent(f"""\
            {repo.database.short_oid(commits[0].oid)} C
            {repo.database.short_oid(commits[1].oid)} B
            {repo.database.short_oid(commits[2].oid)} A
        """)
        assert_stdout(stdout, expected)
    
    
    def test_oneline_without_abbrev(self, legit_cmd, chain_of_commits):
        commits = chain_of_commits
        # run with --pretty=oneline but no abbrev flag
        _, _, stdout, _ = legit_cmd("log", "--pretty=oneline")
        expected = textwrap.dedent(f"""\
            {commits[0].oid} C
            {commits[1].oid} B
            {commits[2].oid} A
        """)
        assert_stdout(stdout, expected)
    
    
    def test_oneline_from_specified_commit(self, legit_cmd, chain_of_commits):
        commits = chain_of_commits
        # start from HEAD^ only
        _, _, stdout, _ = legit_cmd("log", "--pretty=oneline", "@^")
        expected = textwrap.dedent(f"""\
            {commits[1].oid} B
            {commits[2].oid} A
        """)
        assert_stdout(stdout, expected)
    
    
    def test_short_decorations(self, legit_cmd, chain_of_commits):
        commits = chain_of_commits
        # HEAD -> master at C, topic at A
        _, _, stdout, _ = legit_cmd("log", "--pretty=oneline", "--decorate=short")
        expected = textwrap.dedent(f"""\
            {commits[0].oid} (HEAD -> master) C
            {commits[1].oid} B
            {commits[2].oid} (topic) A
        """)
        assert_stdout(stdout, expected)
    
    
    def test_detached_head_decorations(self, legit_cmd, chain_of_commits):
        commits = chain_of_commits
        # detach HEAD at C
        legit_cmd("checkout", "@")
        # now both HEAD and master point at C
        _, _, stdout, _ = legit_cmd("log", "--pretty=oneline", "--decorate=short")
        expected = textwrap.dedent(f"""\
            {commits[0].oid} (HEAD, master) C
            {commits[1].oid} B
            {commits[2].oid} (topic) A
        """)
        assert_stdout(stdout, expected)
    
    
    def test_full_decorations(self, legit_cmd, chain_of_commits):
        commits = chain_of_commits
        # decorate=full shows full ref paths
        _, _, stdout, _ = legit_cmd("log", "--pretty=oneline", "--decorate=full")
        expected = textwrap.dedent(f"""\
            {commits[0].oid} (HEAD -> refs/heads/master) C
            {commits[1].oid} B
            {commits[2].oid} (refs/heads/topic) A
        """)
        assert_stdout(stdout, expected)
    
    
    def test_oneline_with_patches(self, legit_cmd, chain_of_commits):
        commits = chain_of_commits
        # show patches as well
        _, _, stdout, _ = legit_cmd("log", "--pretty=oneline", "--patch")
        expected = textwrap.dedent(f"""\
            {commits[0].oid} C
            diff --git a/file.txt b/file.txt
            index 7371f47..96d80cd 100644
            --- a/file.txt
            +++ b/file.txt
            @@ -1,1 +1,1 @@
            -B
            +C
            {commits[1].oid} B
            diff --git a/file.txt b/file.txt
            index 8c7e5a6..7371f47 100644
            --- a/file.txt
            +++ b/file.txt
            @@ -1,1 +1,1 @@
            -A
            +B
            {commits[2].oid} A
            diff --git a/file.txt b/file.txt
            new file mode 100644
            index 0000000..8c7e5a6
            --- /dev/null
            +++ b/file.txt
            @@ -1,0 +1,1 @@
            +A
        """)
        assert_stdout(stdout, expected)


class TestLogPathFiltering:
    @pytest.fixture(autouse=True)
    def setup_commits(self, commit_tree, load_commit):
        commit_tree("first", {
            "a/1.txt": "1",
            "b/c/2.txt": "2",
        })
        commit_tree("second", {
            "a/1.txt": "10",
            "b/3.txt": "3",
        })
        commit_tree("third", {
            "b/c/2.txt": "4",
        })
        self.commits = [load_commit(rev) for rev in ["@^^", "@^", "@"]]

    def test_logs_commits_that_change_a_file(self, legit_cmd):
        c1, c2, c3 = self.commits  # first, second, third
        # filtering by a/1.txt
        _, _, stdout, _ = legit_cmd("log", "--pretty=oneline", "a/1.txt")
        expected = textwrap.dedent(f"""\
            {c2.oid} second
            {c1.oid} first
        """)
        assert_stdout(stdout, expected)

    def test_logs_commits_that_change_a_directory(self, legit_cmd):
        c1, c2, c3 = self.commits
        _, _, stdout, _ = legit_cmd("log", "--pretty=oneline", "b")
        expected = textwrap.dedent(f"""\
            {c3.oid} third
            {c2.oid} second
            {c1.oid} first
        """)
        assert_stdout(stdout, expected)

    def test_logs_commits_that_change_dir_and_one_of_its_files(self, legit_cmd):
        c1, c2, c3 = self.commits
        _, _, stdout, _ = legit_cmd("log", "--pretty=oneline", "b", "b/3.txt")
        expected = textwrap.dedent(f"""\
            {c3.oid} third
            {c2.oid} second
            {c1.oid} first
        """)
        assert_stdout(stdout, expected)

    def test_logs_commits_that_change_a_nested_directory(self, legit_cmd):
        c1, c2, c3 = self.commits
        _, _, stdout, _ = legit_cmd("log", "--pretty=oneline", "b/c")
        expected = textwrap.dedent(f"""\
            {c3.oid} third
            {c1.oid} first
        """)
        assert_stdout(stdout, expected)

    def test_logs_with_patches_for_selected_files(self, legit_cmd):
        c1, c2, c3 = self.commits
        _, _, stdout, _ = legit_cmd("log", "--pretty=oneline", "--patch", "a/1.txt")
        expected = textwrap.dedent(f"""\
            {c2.oid} second
            diff --git a/a/1.txt b/a/1.txt
            index 56a6051..9a03714 100644
            --- a/a/1.txt
            +++ b/a/1.txt
            @@ -1,1 +1,1 @@
            -1
            +10
            {c1.oid} first
            diff --git a/a/1.txt b/a/1.txt
            new file mode 100644
            index 0000000..56a6051
            --- /dev/null
            +++ b/a/1.txt
            @@ -1,0 +1,1 @@
            +1
        """)
        assert_stdout(stdout, expected)


class TestLogBranchHistory:
    @pytest.fixture(autouse=True)
    def setup_branches(self, commit_file, legit_cmd, resolve_revision):
        # create master-1, master-2, master-3 on master
        for n in range(1, 4):
            commit_file(f"master-{n}")
        # branch off at master^ into topic, then commit topic-1..topic-4
        legit_cmd("branch", "topic", "master^")
        legit_cmd("checkout", "topic")
        self.branch_time = datetime.now() + timedelta(seconds=10)
        for n in range(1, 5):
            commit_file(f"topic-{n}", self.branch_time)
        # capture OIDs for master~0..2 and topic~0..3
        self.master = [resolve_revision(f"master~{n}") for n in range(0, 3)]
        self.topic  = [resolve_revision(f"topic~{n}") for n in range(0, 4)]

    def test_combined_history_of_multiple_branches(self, legit_cmd):
        m, t = self.master, self.topic
        # include both master and topic
        _, _, stdout, _ = legit_cmd(
            "log", "--pretty=oneline", "--decorate=short", "master", "topic"
        )
        expected = textwrap.dedent(f"""\
            {t[0]} (HEAD -> topic) topic-4
            {t[1]} topic-3
            {t[2]} topic-2
            {t[3]} topic-1
            {m[0]} (master) master-3
            {m[1]} master-2
            {m[2]} master-1
        """)
        assert_stdout(stdout, expected)

    def test_diff_from_one_branch_to_another(self, legit_cmd):
        t = self.topic
        # master..topic
        _, _, stdout, _ = legit_cmd("log", "--pretty=oneline", "master..topic")
        expected = textwrap.dedent(f"""\
            {t[0]} topic-4
            {t[1]} topic-3
            {t[2]} topic-2
            {t[3]} topic-1
        """)
        assert_stdout(stdout, expected)

        # master ^topic (only master commits not in topic)
        m0 = self.master[0]
        _, _, stdout, _ = legit_cmd("log", "--pretty=oneline", "master", "^topic")
        expected = textwrap.dedent(f"""\
            {m0} master-3
        """)
        assert_stdout(stdout, expected)

    def test_excludes_long_branch_when_times_equal(self, legit_cmd, commit_file):
        # create a side branch off topic^^ and add 10 commits at same time
        legit_cmd("branch", "side", "topic^^")
        legit_cmd("checkout", "side")
        for n in range(1, 11):
            commit_file(f"side-{n}", self.branch_time)
        _, _, stdout, _ = legit_cmd(
            "log", "--pretty=oneline", "side..topic", "^master"
        )
        expected = textwrap.dedent(f"""\
            {self.topic[0]} topic-4
            {self.topic[1]} topic-3
        """)
        assert_stdout(stdout, expected)

    def test_logs_last_few_commits_on_branch(self, legit_cmd):
        # @~3..  means from HEAD~3..HEAD
        t = self.topic
        _, _, stdout, _ = legit_cmd("log", "--pretty=oneline", "@~3..")
        expected = textwrap.dedent(f"""\
            {t[0]} topic-4
            {t[1]} topic-3
            {t[2]} topic-2
        """)
        assert_stdout(stdout, expected)

