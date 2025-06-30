import textwrap
from typing import Optional
from legit.repository import Repository
from legit.cmd_base import Base
from legit.write_commit import WriteCommitMixin
from legit.editor import Editor
from legit.revision import Revision


COMMIT_NOTES = textwrap.dedent(
    """\
    Please enter the commit message for your changes. Lines starting
    with '#' will be ignored, and an empty message aborts the commit.
    """
)


class Commit(WriteCommitMixin, Base):

    def define_options(self) -> None:
        self.define_write_commit_options()
        
        args_iter = iter(self.args)
        for arg in args_iter:
            if arg.startswith('--reuse-message='):
                self.reuse = arg.split('=', 1)[1]
                self.edit = False
            elif arg == '-C':
                try:
                    self.reuse = next(args_iter)
                    self.edit = False
                except StopIteration:
                    pass
        
            elif arg.startswith('--reedit-message='):
                self.reuse = arg.split('=', 1)[1]
                self.edit = True
            elif arg == '-c':
                try:
                    self.reuse = next(args_iter)
                    self.edit = True
                except StopIteration:
                    pass
 
    def run(self) -> None:
        self.define_options()    

        self.repo = Repository(self.dir / ".git")
        self.repo.index.load()

        if self.repo.pending_commit().is_in_progress():
            self.resume_merge()

        parent = self.repo.refs.read_head()
        message: str = self.compose_message(self.read_message() or self.reused_message())
        commit = self.write_commit([parent] if parent else [], message)
        
        self.print_commit(commit)

        self.exit(0)

    def reused_message(self) -> Optional[str]:
        if not self.reuse:
            return None

        revision = Revision(self.repo, self.reuse)
        commit = self.repo.database.load(revision.resolve())

        return commit.message

    def compose_message(self, message: Optional[str]) -> Optional[str]:
        def editor_setup(editor: Editor):
            editor.println(message or "")
            editor.println("")
            editor.note(COMMIT_NOTES)
    
            if not self.edit:
                editor.close()
    
        return Editor.edit(self.commit_message_path(), block=editor_setup)

