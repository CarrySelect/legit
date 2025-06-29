from pathlib import Path
from typing import Optional
from legit.cmd_base import Base
from legit.repository import Repository
from legit.revision import Revision


class Reset(Base):
    def run(self) -> None:
        self.repo: Repository = Repository(self.dir / ".git")
        self.select_commit_oid()

        self.repo.index.load_for_update()

        for path in self.args:
            self.reset_path(Path(path))

        self.repo.index.write_updates()

        self.exit(0)

    def select_commit_oid(self) -> None:
        revision = self.args[0] if self.args[0] is not None else "HEAD"
        try:
            self.commit_oid = Revision(self.repo, revision).resolve()
        except Revision.InvalidObject:
            self.commit_oid = self.repo.refs.read_head()
        self.args.pop(0)

    def reset_path(self, path: Optional[Path]) -> None:
        listing = self.repo.database.load_tree_list(self.commit_oid, path)
    
        if path is not None:
            self.repo.index.remove(path)

        for path, entry in listing.items():
            self.repo.index.add_from_db(path, entry)


