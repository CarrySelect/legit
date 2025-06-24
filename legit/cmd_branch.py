from legit.cmd_base import Base
from legit.refs import Refs
from legit.repository import Repository


class Branch(Base):
    def run(self) -> None:
        self.repo = Repository(self.dir / ".git")
        self.create_branch()
        self.exit(0)

    def create_branch(self) -> None:
        branch_name = self.args[0]
        try:
            self.repo.refs.create_branch(branch_name)
        except Refs.InvalidBranch as e:
            self.stderr.write(f"fatal: {e}" + '\n')
            self.exit(128)

