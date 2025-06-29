import hashlib
from typing import MutableMapping, Optional, Type
import zlib
import os
import random
import string
from pathlib import Path
from legit.tree import DatabaseEntry, Tree
from legit.commit import Commit
from legit.blob import Blob
from legit.tree_diff import TreeDiff
from legit.pathfilter import PathFilter


TYPES: MutableMapping[str, Type[Blob | Commit | Tree]] = {
    "blob": Blob,
    "commit": Commit,
    "tree": Tree,
}



class Database:
    def __init__(self, path: Path) -> None:
        self.path: Path = path
        self.objects: MutableMapping[str, Blob | Commit | Tree] = {}

    def tree_diff(self, a: str, b: str, pathfilter=PathFilter()) -> dict[Path, list[Optional[DatabaseEntry]]]:
        diff = TreeDiff(self)
        diff.compare_oids(a, b, pathfilter)
        return diff.changes

    def load(self, oid: str) -> Blob | Commit | Tree:
        obj = self.read_object(oid)
        self.objects[oid] = obj
        return obj

    def load_tree_entry(self, oid: str, path: Optional[Path]) -> DatabaseEntry:
        commit = self.load(oid)
        root = DatabaseEntry(commit.tree, 0o40000)

        if path is None:
            return root

        return self.traverse_path_loop(path, root)

    def traverse_path_loop(self, path: Path, root) -> DatabaseEntry:
        entry = root
        for name in path.parts:
            if not entry:
                break
            entry = self.load(entry.oid).entries[name]
        return entry

    def load_tree_list(self, oid: Optional[str], path: Optional[Path]):
        if oid is None:
            return {}

        entry = self.load_tree_entry(oid, path)
        thing = {}
        self.build_list(thing, entry, path if path is not None else Path())
        return thing

    def build_list(self, thing, entry, prefix: Path):
        if entry is None:
            return

        if not entry.is_tree():
            thing[str(prefix)] = entry
            return entry
        
        for name, item in self.load(entry.oid).entries.items():
            self.build_list(thing, item, prefix / name)
    
    def store(self, obj: Blob | Commit | Tree) -> None:
        content = self.serialize_object(obj)
        obj.oid = self.hash_content(content)
        
        self.write_object(obj.oid, content)

    def hash_object(self, obj: Blob | Commit | Tree) -> str:
        return self.hash_content(self.serialize_object(obj))

    def serialize_object(self, obj: Blob | Commit | Tree) -> bytes:
        string = obj.to_bytes()
        header = f"{obj.type()} {len(string)}".encode('utf-8') + b"\x00"

        return header + string

    def hash_content(self, content: bytes) -> str:
        return hashlib.sha1(content).hexdigest()
 
    def write_object(self, oid: str, content: bytes) -> None:
        object_path = self.path / str(oid[:2]) / str(oid[2:])
        if object_path.exists():
            return

        dirname = object_path.parent
        temp_path = dirname / self.generate_temp_name()

        flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
        mode = 0o644

        try:
            file = os.fdopen(os.open(temp_path, flags, mode), "rb+")
        except FileNotFoundError:
            dirname.mkdir(exist_ok=True, parents=True)
            file = os.fdopen(os.open(temp_path, flags, mode), "rb+")

        compressed = zlib.compress(content)
        file.write(compressed)
        file.close()

        temp_path.rename(object_path)

    def read_object(self, oid: str) -> Blob | Commit | Tree:
        object_path = self.path / str(oid[:2]) / str(oid[2:])
        with open(object_path, 'rb') as f:
            bindata = f.read()

        data = zlib.decompress(bindata)

        space_idx = data.index(b" ")
        nul_idx   = data.index(b"\x00", space_idx)

        obj_type = data[:space_idx].decode()
        size     = int(data[space_idx + 1:nul_idx])
        payload  = data[nul_idx + 1:] 
    
        obj = TYPES[obj_type].parse(payload)
        obj.oid = oid

        return obj

    def prefix_match(self, name: str) -> list[str]:
        object_path = self.path / str(name[:2]) / str(name[2:])
        dirname = object_path.parent

        oids = []
        
        try:
            files = dirname.iterdir()
        except FileNotFoundError:
            return []

        for filename in files:
            oids.append(f"{dirname.name}{filename.name}")

        return [oid for oid in oids if oid.startswith(name)]

    def short_oid(self, oid: str) -> str:
        return oid[:7]

    def generate_temp_name(self) -> str:
        return f"tmp_obj_" + ''.join(random.choices(string.ascii_letters + string.digits, k=6))
            
        


