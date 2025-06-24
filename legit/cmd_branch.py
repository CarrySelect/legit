from legit.cmd_base import Base
from legit.refs import Refs
from legit.repository import Repository
from legit.revision import Revision


class Branch(Base):
    def run(self) -> None:
        self.repo = Repository(self.dir / ".git")
        self.create_branch()
        self.exit(0)

    def create_branch(self) -> None:
        branch_name = self.args[0]

        start_oid = None

        try:
            starting_point = self.args[1]
        except IndexError:
            starting_point = None

        if starting_point is not None:
            revision = Revision(self.repo, starting_point)
            try:
                start_oid = revision.resolve(Revision.COMMIT)
            except Revision.InvalidObject as e:
                for err in revision.errors:
                    self.stderr.write(f"error: {e}" + '\n')
                    for line in err.hint:
                        self.stderr.write(f"hint: {line}" + '\n')
                self.stderr.write(f"fatal: {e}" + '\n')
                self.exit(128)
        else:
            start_oid = self.repo.refs.read_head()
    
        try:
            assert start_oid is not None
            self.repo.refs.create_branch(branch_name, start_oid)
        except Refs.InvalidBranch as e:
            self.stderr.write(f"fatal: {e}" + '\n')
            self.exit(128)

