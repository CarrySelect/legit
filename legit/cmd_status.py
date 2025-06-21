from legit.cmd_base import Base
from legit.repository import Repository

class Status(Base):
    def __init__(self, *args):
        super().__init__(*args)
        self.repo = Repository(self.dir / ".git")

    def run(self) -> None:
        self.repo.index.load()

        untracked = [f for f in self.repo.workspace.list_files(self.repo.git_path.parent) if not self.repo.index.is_tracked(f)]
        
        for f in sorted(untracked):
            self.stdout.write(f"?? {f}\n")

        self.exit(0)
