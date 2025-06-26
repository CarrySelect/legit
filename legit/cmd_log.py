from typing import Generator
from legit.cmd_base import Base
from legit.commit import Commit
from legit.repository import Repository


class Log(Base):
    def run(self) -> None:
        self.repo: Repository = Repository(self.dir / ".git")
        self.blank_line: bool = False
        
        self.abbrev = "auto"      # :auto
        self.format = "medium"    # default format
        self.blank_line = False

        for arg in self.args:
            if arg == "--oneline":
                if self.abbrev == "auto":
                    self.abbrev = True
                self.format = "oneline"

            elif arg == "--abbrev-commit":
                self.abbrev = True
            elif arg == "--no-abbrev-commit":
                self.abbrev = False

            elif arg.startswith("--pretty="):
                self.format = arg.split("=", 1)[1]
            elif arg.startswith("--format="):
                self.format = arg.split("=", 1)[1]
   
        self.setup_pager()
        
        for commit in self.each_commit():
            self.show_commit(commit)
        
        self.exit(0)

    def each_commit(self) -> Generator[Commit]:
        oid = self.repo.refs.read_head()

        while oid is not None:
            commit = self.repo.database.load(oid)
            assert isinstance(commit, Commit)
            yield commit
            oid = commit.parent

    def show_commit(self, commit: Commit) -> None:
        match self.format:
            case c if c == "medium":
                self.show_commit_medium(commit)
            case c if c == "oneline":
                self.show_commit_oneline(commit)

    def show_commit_medium(self, commit: Commit) -> None:
        author = commit.author

        self._blank_line()
        self.println(self.fmt("yellow", f"commit {self._abbrev(commit)}"))
        self.println(f"Author: {author.name} <{author.email}>")
        self.println(f"Date:   {author.readable_time()}")
        self._blank_line()

        for line in commit.message.splitlines():
            self.println(f"    {line}")

    def show_commit_oneline(self, commit: Commit) -> None:
        self.println(f"{self.fmt('yellow', self._abbrev(commit))} {commit.title_line()}") 

    def _blank_line(self) -> None:
        if self.blank_line:
            self.println('')
        self.blank_line = True

    def _abbrev(self, commit: Commit) -> str:
        if self.abbrev:
            return self.repo.database.short_oid(commit.oid)
        else:
            return commit.oid
