from pathlib import Path
from legit.repository import Repository
from legit.tree import Tree

repo = Repository(Path.cwd() / ".git")

head_oid = repo.refs.read_head()
commit = repo.database.load(head_oid)

def show_tree(repo: Repository, oid, prefix=''):
    tree: Tree = repo.database.load(oid)

    for name, entry in tree.entries.items():
        path = Path(prefix) / name
        if entry.is_tree():
            show_tree(repo, entry.oid, path)
        else:
            mode = oct(entry.mode)[2:]
            print(f"{mode} {entry.oid} {path}")


show_tree(repo, commit.tree)
