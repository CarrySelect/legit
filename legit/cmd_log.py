from typing import Generator
from legit.cmd_base import Base
from legit.commit import Commit
from legit.refs import Refs
from legit.repository import Repository
from legit.print_diff import PrintDiffMixin, Target


class Log(PrintDiffMixin, Base):
    def run(self) -> None:
        self.patch = False
        self.define_print_diff_options()

        self.repo: Repository = Repository(self.dir / ".git")
        self.blank_line: bool = False
        
        self.abbrev = "auto"
        self.format = "medium"
        self.blank_line = False
        self.decorate = "auto"

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

            elif arg.startswith("--decorate="):
                self.decorate = arg.split("=", 1)[1] or "short"
            elif arg == "--no-decorate":
                self.decorate = "no"
   
        self.setup_pager()

        self.reverse_refs = self.repo.refs.reverse_refs()
        self.current_ref = self.repo.refs.current_ref()
        
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

        self.show_patch(commit)

    def show_patch(self, commit: Commit) -> None:
        if not self.patch:
            return

        diff = self.repo.database.tree_diff(commit.parent, commit.oid)
        paths = sorted(diff.keys())

        self._blank_line()

        for path in paths:
            old_item, new_item = diff[path]
            self.print_diff(self.from_diff_item(path, old_item), self.from_diff_item(path, new_item))

    def from_diff_item(self, path, item) -> Target:
        if item is not None:
            blob = self.repo.database.load(item.oid)
            return Target(path, item.oid, oct(item.mode())[2:], blob.data)
        else:
            return Target(path, '0' * 40, None, '')

    def show_commit_medium(self, commit: Commit) -> None:
        author = commit.author

        self._blank_line()
        self.println(self.fmt("yellow", f"commit {self._abbrev(commit)}") + self._decorate(commit))
        self.println(f"Author: {author.name} <{author.email}>")
        self.println(f"Date:   {author.readable_time()}")
        self._blank_line()

        for line in commit.message.splitlines():
            self.println(f"    {line}")

    def show_commit_oneline(self, commit: Commit) -> None:
        _id = self.fmt('yellow', self._abbrev(commit)) + self._decorate(commit) 
        self.println(f"{_id} {commit.title_line()}") 

    def is_target(self, ref):
        return ref.is_head() and not self.current_ref.is_head()

    def _decorate(self, commit: Commit) -> str:
        if self.decorate == 'auto':
            if not self.isatty:
                return ''
        elif self.decorate == 'no':
            return ''

        refs = self.reverse_refs[commit.oid]
        if not refs:
            return ''

        head = [r for r in refs if self.is_target(r)]
        print(f"{head=}")
        refs = [r for r in refs if not self.is_target(r)]
        print(f"{refs=}")

        names = [self.decoration_name(head[0] if head else None, ref) for ref in refs]

        return self.fmt("yellow", " (") + self.fmt("yellow", ", ").join(names) + self.fmt("yellow", ")")
    
    def decoration_name(self, head, ref):
        if self.decorate == 'short' or self.decorate == 'auto':
            name = ref.short_name()
        elif self.decorate == 'full':
            name = ref.path

        name = self.fmt(self.ref_color(ref), name)

        if head and ref == self.current_ref:
            name = self.fmt(self.ref_color(head), f"{head.path} -> {name}")

        return name

    def ref_color(self, ref):
        return ["bold", "cyan"] if ref.is_head() else ["bold", "green"]
    
    def _blank_line(self) -> None:
        if self.format == 'oneline':
            return
        if self.blank_line:
            self.println('')
        self.blank_line = True

    def _abbrev(self, commit: Commit) -> str:
        if self.abbrev:
            return self.repo.database.short_oid(commit.oid)
        else:
            return commit.oid
