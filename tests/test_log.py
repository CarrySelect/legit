import pytest
import time
from datetime import datetime, timezone, timedelta
from io import StringIO
from legit.command import Command


from tests.cmd_helper import assert_stdout, write_file, repo_path, legit_cmd, commit, resolve_revision, repo

@pytest.fixture
def load_commit(repo, resolve_revision):
    def _load_commit(revision_expression):
        oid = resolve_revision(revision_expression)
        return repo.database.load(oid)
    return _load_commit

def commit_file(write_file, legit_cmd, commit, message, commit_time=None):
    """
    Writes to a standard file, adds it, and commits.
    An optional commit_time can be provided.
    """
    write_file("file.txt", message)
    legit_cmd("add", ".")
    
    # The 'commit' fixture handles the author environment. We can add the date.
    env = {}
    if commit_time:
        # Format the time for GIT_AUTHOR_DATE environment variable
        formatted_time = commit_time.strftime("%s %z")
        env["GIT_AUTHOR_DATE"] = formatted_time
        
    author_env = {
        "GIT_AUTHOR_NAME": "A. U. Thor",
        "GIT_AUTHOR_EMAIL": "author@example.com",
    }
    
    # Combine the environments
    full_env = {**author_env, **env}

    # Use a modified commit command call that accepts an environment
    stdin = StringIO(message)
    stdout = StringIO()
    stderr = StringIO()
    Command.execute(
        repo_path, full_env, ["legit", "commit"], stdin, stdout, stderr
    )


# Helper function to commit a tree of multiple files
def commit_tree(write_file, legit_cmd, commit, message, files):
    """
    Writes a dictionary of files, adds them, and commits.
    """
    for path, contents in files.items():
        write_file(path, contents)
    legit_cmd("add", ".")
    commit(message)


class TestLogWithChainOfCommits:
    @pytest.fixture(autouse=True)
    def setup(self, write_file, legit_cmd, commit, load_commit, repo):
        """
        Setup for tests with a simple linear chain of commits.
        o---o---o
        A   B   C
        """
        messages = ["A", "B", "C"]
        for msg in messages:
            commit_file(write_file, legit_cmd, commit, msg)

        legit_cmd("branch", "topic", "@^^")

        self.commits = [load_commit(rev) for rev in ["@", "@^", "@^^"]]
        self.repo = repo

    def test_log_medium_format(self, legit_cmd):
        _, _, stdout, _ = legit_cmd("log")
        
        expected = f"""\
commit {self.commits[0].oid}
Author: A. U. Thor <author@example.com>
Date:   {self.commits[0].author.readable_time()}

    C

commit {self.commits[1].oid}
Author: A. U. Thor <author@example.com>
Date:   {self.commits[1].author.readable_time()}

    B

commit {self.commits[2].oid}
Author: A. U. Thor <author@example.com>
Date:   {self.commits[2].author.readable_time()}

    A
"""
        assert_stdout(stdout, expected)

    def test_log_medium_format_abbreviated(self, legit_cmd):
        _, _, stdout, _ = legit_cmd("log", "--abbrev-commit")

        expected = f"""\
commit {self.repo.database.short_oid(self.commits[0].oid)}
Author: A. U. Thor <author@example.com>
Date:   {self.commits[0].author.readable_time()}

    C

commit {self.repo.database.short_oid(self.commits[1].oid)}
Author: A. U. Thor <author@example.com>
Date:   {self.commits[1].author.readable_time()}

    B

commit {self.repo.database.short_oid(self.commits[2].oid)}
Author: A. U. Thor <author@example.com>
Date:   {self.commits[2].author.readable_time()}

    A
"""
        assert_stdout(stdout, expected)
        
    def test_log_oneline_format(self, legit_cmd):
        _, _, stdout, _ = legit_cmd("log", "--oneline")

        expected = f"""\
{self.repo.database.short_oid(self.commits[0].oid)} C
{self.repo.database.short_oid(self.commits[1].oid)} B
{self.repo.database.short_oid(self.commits[2].oid)} A
"""
        assert_stdout(stdout, expected)

    def test_log_oneline_no_abbrev(self, legit_cmd):
        _, _, stdout, _ = legit_cmd("log", "--pretty=oneline")

        expected = f"""\
{self.commits[0].oid} C
{self.commits[1].oid} B
{self.commits[2].oid} A
"""
        assert_stdout(stdout, expected)

    def test_log_from_specific_commit(self, legit_cmd):
        _, _, stdout, _ = legit_cmd("log", "--pretty=oneline", "@^")

        expected = f"""\
{self.commits[1].oid} B
{self.commits[2].oid} A
"""
        assert_stdout(stdout, expected)

    def test_log_short_decorations(self, legit_cmd):
        _, _, stdout, _ = legit_cmd("log", "--pretty=oneline", "--decorate=short")
        
        short_oids = [self.repo.database.short_oid(c.oid) for c in self.commits]

        expected = f"""\
{short_oids[0]} (HEAD -> master) C
{short_oids[1]} B
{short_oids[2]} (topic) A
"""
        # The Python translation uses full OIDs here to match the ruby test logic
        expected_full_oid = f"""\
{self.commits[0].oid} (HEAD -> master) C
{self.commits[1].oid} B
{self.commits[2].oid} (topic) A
"""
        assert_stdout(stdout, expected_full_oid)

    def test_log_detached_head(self, legit_cmd):
        legit_cmd("checkout", "@")
        _, _, stdout, _ = legit_cmd("log", "--pretty=oneline", "--decorate=short")

        expected = f"""\
{self.commits[0].oid} (HEAD, master) C
{self.commits[1].oid} B
{self.commits[2].oid} (topic) A
"""
        assert_stdout(stdout, expected)

    def test_log_full_decorations(self, legit_cmd):
        _, _, stdout, _ = legit_cmd("log", "--pretty=oneline", "--decorate=full")

        expected = f"""\
{self.commits[0].oid} (HEAD -> refs/heads/master) C
{self.commits[1].oid} B
{self.commits[2].oid} (refs/heads/topic) A
"""
        assert_stdout(stdout, expected)

    def test_log_with_patches(self, legit_cmd):
        _, _, stdout, _ = legit_cmd("log", "--pretty=oneline", "--patch")
        
        expected = f"""\
{self.commits[0].oid} C
diff --git a/file.txt b/file.txt
index 7371f47..96d80cd 100644
--- a/file.txt
+++ b/file.txt
@@ -1,1 +1,1 @@
-B
+C
{self.commits[1].oid} B
diff --git a/file.txt b/file.txt
index 8c7e5a6..7371f47 100644
--- a/file.txt
+++ b/file.txt
@@ -1,1 +1,1 @@
-A
+B
{self.commits[2].oid} A
diff --git a/file.txt b/file.txt
new file mode 100644
index 0000000..8c7e5a6
--- /dev/null
+++ b/file.txt
@@ -0,0 +1,1 @@
+A
"""
        assert_stdout(stdout, expected)

class TestLogWithFileChanges:
    @pytest.fixture(autouse=True)
    def setup(self, write_file, legit_cmd, commit, load_commit):
        commit_tree(write_file, legit_cmd, commit, "first", {
            "a/1.txt": "1",
            "b/c/2.txt": "2"
        })
        commit_tree(write_file, legit_cmd, commit, "second", {
            "a/1.txt": "10",
            "b/3.txt": "3"
        })
        commit_tree(write_file, legit_cmd, commit, "third", {
            "b/c/2.txt": "4"
        })

        self.commits = [load_commit(rev) for rev in ["@^^", "@^", "@"]]
        
    def test_log_commits_changing_file(self, legit_cmd):
        _, _, stdout, _ = legit_cmd("log", "--pretty=oneline", "a/1.txt")
        
        expected = f"""\
{self.commits[1].oid} second
{self.commits[0].oid} first
"""
        assert_stdout(stdout, expected)

    def test_log_commits_changing_directory(self, legit_cmd):
        _, _, stdout, _ = legit_cmd("log", "--pretty=oneline", "b")
        
        expected = f"""\
{self.commits[2].oid} third
{self.commits[1].oid} second
{self.commits[0].oid} first
"""
        assert_stdout(stdout, expected)

    def test_log_commits_changing_dir_and_file(self, legit_cmd):
        _, _, stdout, _ = legit_cmd("log", "--pretty=oneline", "b", "b/3.txt")

        expected = f"""\
{self.commits[2].oid} third
{self.commits[1].oid} second
{self.commits[0].oid} first
"""
        assert_stdout(stdout, expected)
        
    def test_log_commits_changing_nested_directory(self, legit_cmd):
        _, _, stdout, _ = legit_cmd("log", "--pretty=oneline", "b/c")

        expected = f"""\
{self.commits[2].oid} third
{self.commits[0].oid} first
"""
        assert_stdout(stdout, expected)

    def test_log_with_patches_for_selected_files(self, legit_cmd):
        _, _, stdout, _ = legit_cmd("log", "--pretty=oneline", "--patch", "a/1.txt")

        expected = f"""\
{self.commits[1].oid} second
diff --git a/a/1.txt b/a/1.txt
index 56a6051..9a03714 100644
--- a/a/1.txt
+++ b/a/1.txt
@@ -1,1 +1,1 @@
-1
+10
{self.commits[0].oid} first
diff --git a/a/1.txt b/a/1.txt
new file mode 100644
index 0000000..56a6051
--- /dev/null
+++ b/a/1.txt
@@ -0,0 +1,1 @@
+1
"""
        assert_stdout(stdout, expected)


class TestLogWithTreeOfCommits:
    @pytest.fixture(autouse=True)
    def setup(self, write_file, legit_cmd, commit, resolve_revision):
        for n in range(1, 4):
            commit_file(write_file, legit_cmd, commit, f"master-{n}")

        legit_cmd("branch", "topic", "master^")
        legit_cmd("checkout", "topic")
        
        self.branch_time = datetime.now(timezone.utc) + timedelta(seconds=10)
        for n in range(1, 5):
            commit_file(write_file, legit_cmd, commit, f"topic-{n}", self.branch_time)

        self.master_oids = [resolve_revision(f"master~{n}") for n in range(3)]
        self.topic_oids = [resolve_revision(f"topic~{n}") for n in range(4)]

    def test_log_combined_history(self, legit_cmd):
        _, _, stdout, _ = legit_cmd("log", "--pretty=oneline", "--decorate=short", "master", "topic")

        expected = f"""\
{self.topic_oids[0]} (HEAD -> topic) topic-4
{self.topic_oids[1]} topic-3
{self.topic_oids[2]} topic-2
{self.topic_oids[3]} topic-1
{self.master_oids[0]} (master) master-3
{self.master_oids[1]} master-2
{self.master_oids[2]} master-1
"""
        assert_stdout(stdout, expected)

    def test_log_branch_difference(self, legit_cmd):
        _, _, stdout, _ = legit_cmd("log", "--pretty=oneline", "master..topic")

        expected = f"""\
{self.topic_oids[0]} topic-4
{self.topic_oids[1]} topic-3
{self.topic_oids[2]} topic-2
{self.topic_oids[3]} topic-1
"""
        assert_stdout(stdout, expected)
        
        _, _, stdout, _ = legit_cmd("log", "--pretty=oneline", "master", "^topic")
        
        expected = f"""\
{self.master_oids[0]} master-3
"""
        assert_stdout(stdout, expected)

    def test_exclude_long_branch_with_equal_times(self, write_file, legit_cmd, commit):
        legit_cmd("branch", "side", "topic^^")
        legit_cmd("checkout", "side")

        for n in range(1, 11):
            commit_file(write_file, legit_cmd, commit, f"side-{n}", self.branch_time)
            
        _, _, stdout, _ = legit_cmd("log", "--pretty=oneline", "side..topic", "^master")
        
        expected = f"""\
{self.topic_oids[0]} topic-4
{self.topic_oids[1]} topic-3
"""
        assert_stdout(stdout, expected)

    def test_log_last_few_commits(self, legit_cmd):
        _, _, stdout, _ = legit_cmd("log", "--pretty=oneline", "@~3..")

        expected = f"""\
{self.topic_oids[0]} topic-4
{self.topic_oids[1]} topic-3
{self.topic_oids[2]} topic-2
"""
        assert_stdout(stdout, expected)
