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
        self.resolve_merge()
        self.commit_merge()
        
        self.exit(0)

    def resolve_merge(self) -> None:
        self.repo.index.load_for_update()
        
        merge = Resolve(self.repo, self.inputs)
        merge.execute()

        self.repo.index.write_updates()

    def commit_merge(self) -> None:
        parents = [self.inputs.left_oid, self.inputs.right_oid]
        message = self.stdin.read()
        self.write_commit(parents, message)

