from pathlib import Path
import textwrap
from datetime import datetime
from typing import Optional
from legit.author import Author
from legit.commit import Commit as CommitObject
from legit.tree import Tree
from legit.editor import Editor


CONFLICT_MESSAGE: str = textwrap.dedent("""\
    hint: Fix them up in the work tree, and then use 'legit add/rm <file>'
    hint: as appropriate to mark resolution and make a commit.
    fatal: Exiting because of an unresolved conflict.
""")

MERGE_NOTES: str = textwrap.dedent(
    """\
    It looks like you may be committing a merge.
    If this is not correct, please remove the file
    \t.git/MERGE_HEAD
    and try again.
    """
)

COMMIT_NOTES = textwrap.dedent(
    """\
    Please enter the commit message for your changes. Lines starting
    with '#' will be ignored, and an empty message aborts the commit.
    """
)


class WriteCommitMixin:
    def commit_message_path(self) -> Path:
        return self.repo.git_path / "COMMIT_EDITMSG"

    def read_message(self) -> str:
        if self.message is not None:
            return f"{self.message}\n"
        elif self.file is not None:
            return self.file.read_text()

    def define_write_commit_options(self):
        self.message = None
        self.file = None
        self.edit = 'auto'
    
        args_iter = iter(self.args)
        for arg in args_iter:
            if arg in ('-e', '--edit'):
                self.edit = True
            elif arg == '--no-edit':
                self.edit = False
    
            elif arg.startswith('--message='):
                self.message = arg.split('=', 1)[1]
                if self.edit == 'auto': 
                    self.edit = False
            elif arg == '-m':
                try:
                    self.message = next(args_iter)
                    if self.edit == 'auto':
                        self.edit = False
                except StopIteration:
                    pass
    
            elif arg.startswith('--file='):
                file_path = arg.split('=', 1)[1]
                self.file = self.expanded_path(file_path)
                if self.edit == 'auto':
                    self.edit = False
            elif arg == '-F':
                try:
                    file_path = next(args_iter)
                    self.file = self.expanded_path(file_path)
                    if self.edit == 'auto':
                        self.edit = False
                except StopIteration:
                    pass

    def print_commit(self, commit: CommitObject) -> None:
        ref = self.repo.refs.current_ref()
        info = "detached HEAD" if ref.is_head() else ref.short_name()
        oid = self.repo.database.short_oid(commit.oid)

        if commit.parent is None:
            info += " (root-commit)"
        info += f" {oid}"

        self.println(f"[{info}] {commit.title_line()}")

    def write_commit(self, parents, message):
        tree = self.write_tree()

        name  = self.env.get("GIT_AUTHOR_NAME",  "A. U. Thor")
        email = self.env.get("GIT_AUTHOR_EMAIL", "author@example.com")

        author = Author(name, email, datetime.now().astimezone())
        
        commit = CommitObject([p for p in parents if p], tree.oid, author, message)
        self.repo.database.store(commit)
        self.repo.refs.update_head(commit.oid)

        return commit

    def write_tree(self):
        root = Tree.from_entries(self.repo.index.entries)
        root.traverse(lambda tree: self.repo.database.store(tree))
        return root

    def resume_merge(self):
        self.handle_conflicted_index()
        parents = [self.repo.refs.read_head(), self.repo.pending_commit().merge_oid]
        message = self.compose_merge_message(MERGE_NOTES)
        self.write_commit(parents, message)
        self.repo.pending_commit().clear()
        self.exit(0)

    def handle_conflicted_index(self) -> None:
        if not self.repo.index.is_conflict():
            return

        message = "Committing is not possible because you have unmerged files"
        self.stderr.write(f"error: {message}." + '\n')
        self.stderr.write(CONFLICT_MESSAGE)

        self.exit(128)


    def compose_merge_message(self, notes: Optional[str] = None) -> Optional[str]:
        def editor_setup(editor: Editor):
            editor.println(self.repo.pending_commit().merge_message)
            if notes is not None:
                editor.note(notes)
            editor.println("")
            editor.note(COMMIT_NOTES)
    
            if not self.edit:
                editor.close()
    
        return Editor.edit(self.commit_message_path(), block=editor_setup)


