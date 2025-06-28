from legit.cmd_base import Base
from legit.repository import Repository
from legit.revision import Revision
from legit.common_ancestors import CommonAncestors
from legit.write_commit import WriteCommitMixin
from legit.bases import Bases
from legit.inputs import Inputs
from legit.resolve import Resolve


class Merge(WriteCommitMixin, Base):
    def run(self) -> None:
        self.repo = Repository(self.dir / ".git")

        self.inputs = Inputs(self.repo, "HEAD", self.args[0])

        if self.inputs.are_already_merged():
            self.handle_merged_ancestor()

        if self.inputs.are_fast_forward():
            self.handle_fast_forward()

        self.resolve_merge()
        self.commit_merge()
        
        self.exit(0)

    def resolve_merge(self) -> None:
        self.repo.index.load_for_update()
        
        merge = Resolve(self.repo, self.inputs)
        merge.on_progress(lambda info: self.println(info))
        merge.execute()

        self.repo.index.write_updates()
        if self.repo.index.is_conflict():
            self.println("Automatic merge failed; fix conflicts and then commit the result.")
            self.exit(1)

    def commit_merge(self) -> None:
        parents = [self.inputs.left_oid, self.inputs.right_oid]
        message = self.stdin.read()
        self.write_commit(parents, message)

    def handle_merged_ancestor(self) -> None:
        self.println("Already up to date.")
        self.exit(0)

    def handle_fast_forward(self) -> None:
        a = self.repo.database.short_oid(self.inputs.left_oid)
        b = self.repo.database.short_oid(self.inputs.right_oid)

        self.println(f"Updating {a}..{b}")
        self.println("Fast-forward")

        self.repo.index.load_for_update()

        tree_diff = self.repo.database.tree_diff(self.inputs.left_oid, self.inputs.right_oid)
        self.repo.migration(tree_diff).apply_changes()

        self.repo.index.write_updates()
        self.repo.refs.update_head(self.inputs.right_oid)

        self.exit(0)
