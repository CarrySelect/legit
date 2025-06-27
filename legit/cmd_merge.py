from legit.cmd_base import Base
from legit.repository import Repository
from legit.revision import Revision
from legit.common_ancestors import CommonAncestors
from legit.write_commit import WriteCommitMixin
from legit.bases import Bases

class Merge(WriteCommitMixin, Base):
    def run(self) -> None:
        self.repo = Repository(self.dir / ".git")

        head_oid = self.repo.refs.read_head()
        revision = Revision(self.repo, self.args[0])
        merge_oid = revision.resolve(Revision.COMMIT)

        common = Bases(self.repo.database, head_oid, merge_oid)
        base_oid = common.find()

        self.repo.index.load_for_update()

        tree_diff = self.repo.database.tree_diff(base_oid, merge_oid)
        migration = self.repo.migration(tree_diff)
        migration.apply_changes()

        self.repo.index.write_updates()

        message = self.stdin.read()
        self.write_commit([head_oid, merge_oid], message)

        self.exit(0)
