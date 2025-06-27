from typing import Generator
from legit.cmd_base import Base
from legit.commit import Commit
from legit.refs import Refs
from legit.repository import Repository
from legit.print_diff import PrintDiffMixin, Target
from legit.revision import Revision
from legit.rev_list import RevList


class Log(PrintDiffMixin, Base):
    def run(self) -> None:
        """
        Executes the log command, parsing options and displaying commit history.
        """
        self.repo: Repository = Repository(self.dir / ".git")
        self.blank_line: bool = False
        
        # Set default option values
        self.abbrev = None
        self.format = "medium"
        self.decorate = "auto"
        self.patch = False

        # This list will hold only the non-option arguments (revisions and paths)
        positional_args = []

        # Manually parse options from self.args and filter them from positional_args
        # This ensures that only revisions and paths are passed to RevList.
        for arg in self.args:
            if arg == "--oneline":
                if self.abbrev is None:
                    self.abbrev = True
                self.format = "oneline"
                continue

            if arg == "--abbrev-commit":
                self.abbrev = True
                continue
            if arg == "--no-abbrev-commit":
                self.abbrev = False
                continue

            if arg.startswith("--pretty=") or arg.startswith("--format="):
                self.format = arg.split("=", 1)[1]
                continue
            
            if arg.startswith("--decorate="):
                parts = arg.split("=", 1)
                # Handle '--decorate' with no value, defaulting to 'short'
                self.decorate = parts[1] if len(parts) > 1 and parts[1] else "short"
                continue
            
            if arg == "--no-decorate":
                self.decorate = "no"
                continue
            
            # Allow for -p as a patch flag
            if arg == "--patch" or arg == "-p":
                self.patch = True
                continue
            
            # If it's not a recognized option, it must be a revision or path
            positional_args.append(arg)


        # Initialize diff/patch options and pager now that flags are parsed
        self.define_print_diff_options()
        self.setup_pager()

        # Prepare data for decorating commits
        self.reverse_refs = self.repo.refs.reverse_refs()
        self.current_ref = self.repo.refs.current_ref()
    
        # Use the cleaned list of arguments for RevList
        self.rev_list: RevList = RevList(self.repo, positional_args)
        
        # Iterate through the resolved commits and display them
        for commit in self.rev_list.each():
            self.show_commit(commit)
        
        self.exit(0)

    def show_commit(self, commit: Commit) -> None:
        match self.format:
            case c if c == "medium":
                self.show_commit_medium(commit)
            case c if c == "oneline":
                self.show_commit_oneline(commit)

        self.show_patch(commit)

    def show_patch(self, commit: Commit) -> None:
        if not self.patch or len(commit.parents) > 1:
            return

        diff = self.rev_list.tree_diff(commit.parent, commit.oid)
        paths = sorted(diff.keys())

        self._blank_line()

        for path in paths:
            old_item, new_item = diff[path]
            self.print_diff(self.from_diff_item(path, old_item), self.from_diff_item(path, new_item))

    def from_diff_item(self, path, item) -> Target:
        if item is not None:
            blob = self.repo.database.load(item.oid)
            return Target(path, item.oid, oct(item.mode)[2:], blob.data)
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
        refs = [r for r in refs if not self.is_target(r)]

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
