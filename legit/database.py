import hashlib
import zlib
import os
import random
import string
from pathlib import Path
from legit.tree import Tree
from legit.commit import Commit
from legit.blob import Blob


class Database:
    def __init__(self, path: Path) -> None:
        self.path: Path = path

    def store(self, obj: Blob | Commit | Tree) -> None:
        string = obj.to_bytes()
        header = f"{obj.type()} {len(string)}".encode('utf-8') + b"\x00"

        content = header + string

        obj.oid = hashlib.sha1(content).hexdigest()
        self.write_object(obj.oid, content)

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

    def generate_temp_name(self) -> str:
        return f"tmp_obj_" + ''.join(random.choices(string.ascii_letters + string.digits, k=6))
            
        


