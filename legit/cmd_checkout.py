from pathlib import Path
from typing import cast
from legit.cmd_base import Base
from legit.migration import Migration
from legit.repository import Repository
from legit.revision import Revision
from legit.tree import DatabaseEntry


class Checkout(Base):
    def run(self) -> None:
        self.repo: Repository = Repository(self.dir / ".git")
        
        self.target: str = self.args[0]
        self.current_oid: str = self.repo.refs.read_head()
        
        revision: Revision = Revision(self.repo, self.target)
    
        self.target_oid: str | None = None
        
        try:
            self.target_oid = revision.resolve(Revision.COMMIT)
        except Revision.InvalidObject as e:
            self.handle_invalid_object(revision, e)

        self.repo.index.load_for_update()
        
        assert self.target_oid is not None
        tree_diff = self.repo.database.tree_diff(self.current_oid, self.target_oid)
        migration = self.repo.migration(cast(dict[Path, list[DatabaseEntry]], tree_diff))
        
        try:
            migration.apply_changes()
        except Migration.Conflict:
            self.handle_migration_conflict(migration)

        self.repo.index.write_updates()
        self.repo.refs.update_head(self.target_oid)
        
        self.exit(0)

    def handle_migration_conflict(self, migration: Migration) -> None:
        self.repo.index.release_lock()

        for msg in migration.errors:
            self.stderr.write(f"error: {msg}" + '\n')
        self.stderr.write("Aborting\n")

        self.exit(1)

    def handle_invalid_object(self, revision: Revision, e: Revision.InvalidObject) -> None:
        for err in revision.errors:
            self.stderr.write(f"error: {err}" + '\n')
            for line in err.hint:
                self.stderr.write(f"hint: {line}" + '\n')
        self.stderr.write(f"error: {e}" + '\n')
        self.exit(1)
