from legit.cmd_base import Base
from legit.repository import Repository
from legit.revision import Revision
from legit.tree_diff import TreeDiff


class Checkout(Base):
    def run(self) -> None:
        self.repo: Repository = Repository(self.dir / ".git")
        
        self.target: str = self.args[0]
        self.current_oid: str = self.repo.refs.read_head()
        
        revision: Revision = Revision(self.repo, self.target)

        try:
            self.target_oid = revision.resolve(Revision.COMMIT)
        except Revision.InvalidObject as e:
            self.handle_invalid_object(revision, e)
        
        tree_diff = self.repo.database.tree_diff(self.current_oid, self.target)
        migration = self.repo.migration(tree_diff)

        migration.apply_changes()
        
        self.exit(0)

    def handle_invalid_object(self, revision: Revision, e: Revision.InvalidObject) -> None:
        for err in revision.errors:
            self.stderr.write(f"error: {err}" + '\n')
            for line in err.hint:
                self.stderr.write(f"hint: {line}" + '\n')
        self.stderr.write(f"error: {e}" + '\n')
        self.exit(1)
