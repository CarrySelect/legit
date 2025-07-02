import zlib
import hashlib
import struct

from legit.pack import COMMIT, BLOB, TREE, HEADER_FORMAT, SIGNATURE, VERSION
from legit.numbers import VarIntLE


class Writer:
    class Entry:
        def __init__(self, oid, ty) -> None:
            self.oid = oid
            self.ty = ty

    def __init__(self, output, database, options={}):
        self.output = output
        self.digest = hashlib.sha1()
        self.database = database
        self.compression = options.get("compression", zlib.Z_DEFAULT_COMPRESSION)

    def write_objects(self, rev_list):
        self.prepare_pack_list(rev_list)
        self.write_header()
        self.write_entries()
        self.output.write(self.digest.digest())

    def write(self, data: bytes):
        self.output.write(data)
        self.digest.update(data)

    def prepare_pack_list(self, rev_list):
        self.pack_list = []
        for obj in rev_list.each():
            self.add_to_pack_list(obj)

    def add_to_pack_list(self, obj):
        from legit.database import DatabaseEntry
        from legit.commit import Commit

        if isinstance(obj, Commit):
            self.pack_list.append(Writer.Entry(obj.oid, COMMIT))
        elif isinstance(obj, DatabaseEntry):
            ty = TREE if obj.is_tree() else BLOB
            self.pack_list.append(Writer.Entry(obj.oid, ty))

    def write_header(self):
        header = struct.pack(HEADER_FORMAT, SIGNATURE, VERSION, len(self.pack_list))
        self.write(header)

    def write_entries(self):
        for entry in self.pack_list:
            self.write_entry(entry)

    def write_entry(self, entry: 'Writer.Entry'):
        obj = self.database.load_raw(entry.oid)

        header = VarIntLE.write(obj.size)
        header_list = list(header)
        header_list[0] |= (entry.ty << 4)
        self.write(bytes(header_list))
        compressed = zlib.compress(obj.data, self.compression)
        self.write(compressed)
