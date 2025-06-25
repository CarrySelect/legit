from legit.cmd_base import Base
from legit.refs import Refs
from legit.repository import Repository
from legit.revision import Revision


class Branch(Base):
    def run(self) -> None:
        self.repo = Repository(self.dir / ".git")

        if any(x in self.args for x in {'-v', '-vv', '-vvv', '--verbose'}):
            self.verbose = True
        else:
            self.verbose = False

        if not self.args:
            self.list_branches()
        else:
            self.create_branch()
        self.exit(0)

    def list_branches(self) -> None:
        current = self.repo.refs.current_ref()
        branches = sorted(self.repo.refs.list_branches(), key=lambda ref: ref.path)
        max_width = max((len(b.short_name()) for b in branches), default=0)

        self.setup_pager()

        for ref in branches:
            info = self.format_ref(ref, current)
            info += self.extended_branch_info(ref, max_width)
            self.println(info)

    def format_ref(self, ref, current) -> str:
        if ref == current:
            return f"* {self.fmt('green', ref.short_name())}"
        else:
            return f"  {ref.short_name()}"

    def extended_branch_info(self, ref, max_width) -> str:
        if not self.verbose:
            return ''

        commit = self.repo.database.load(ref.read_oid())
        short = self.repo.database.short_oid(commit.oid)
        space = ' ' * (max_width - len(ref.short_name()))

        return f"{space} {short} {commit.title_line()}"

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

