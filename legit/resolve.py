from legit.repository import Repository
from legit.inputs import Inputs


class Resolve:
    def __init__(self, repo: Repository, inputs: Inputs) -> None:
        self.repo: Repository = repo
        self.inputs: Inputs = inputs

    def execute(self) -> None:
        base_oid = self.inputs.base_oids[0]
        tree_diff = self.repo.database.tree_diff(base_oid, self.inputs.right_oid)
        migration = self.repo.migration(tree_diff)
        migration.apply_changes()
