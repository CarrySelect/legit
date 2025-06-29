import textwrap
from datetime import datetime
from legit.author import Author
from legit.commit import Commit as CommitObject
from legit.tree import Tree


CONFLICT_MESSAGE: str = textwrap.dedent("""\
    hint: Fix them up in the work tree, and then use 'legit add/rm <file>'
    hint: as appropriate to mark resolution and make a commit.
    fatal: Exiting because of an unresolved conflict.
""")


class WriteCommitMixin:
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
        self.write_commit(parents, self.repo.pending_commit().merge_message)
        self.repo.pending_commit().clear()
        self.exit(0)

    def handle_conflicted_index(self) -> None:
        if not self.repo.index.is_conflict():
            return

        message = "Committing is not possible because you have unmerged files"
        self.stderr.write(f"error: {message}." + '\n')
        self.stderr.write(CONFLICT_MESSAGE + '\n')

        self.exit(128)



