import textwrap
from typing import Optional
from legit.repository import Repository
from legit.cmd_base import Base
from legit.write_commit import WriteCommitMixin
from legit.editor import Editor


COMMIT_NOTES = textwrap.dedent(
    """\
    Please enter the commit message for your changes. Lines starting
    with '#' will be ignored, and an empty message aborts the commit.
    """
)


class Commit(WriteCommitMixin, Base):
    def run(self) -> None:
        self.define_write_commit_options()

        self.repo = Repository(self.dir / ".git")
        self.repo.index.load()

        if self.repo.pending_commit().is_in_progress():
            self.resume_merge()

        parent = self.repo.refs.read_head()
        message: str = self.compose_message(self.read_message())
        commit = self.write_commit([parent] if parent else [], message)
        
        self.print_commit(commit)

        self.exit(0)

    def compose_message(self, message: Optional[str]) -> Optional[str]:
        def editor_setup(editor: Editor):
            editor.println(message or "")
            editor.println("")
            editor.note(COMMIT_NOTES)
    
            if not self.edit:
                editor.close()
    
        return Editor.edit(self.commit_message_path(), block=editor_setup)

