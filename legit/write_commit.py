from datetime import datetime
from legit.author import Author
from legit.commit import Commit as CommitObject
from legit.tree import Tree

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


