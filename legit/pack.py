HEADER_SIZE = 12
HEADER_FORMAT = ">4sII"
SIGNATURE = b"PACK"
VERSION = 2

COMMIT = 1
TREE = 2
BLOB = 3

TYPE_CODES = {
    "commit": COMMIT,
    "tree":   TREE,
    "blob":   BLOB,
}

class InvalidPack(Exception):
    pass

class Record:
    def __init__(self, ty, data):
        self.ty = ty
        self.data = data
        self.oid = None

    def __str__(self):
        return self.data.decode('utf-8', errors='replace')

    def to_bytes(self):
        return self.data

    def type(self):
        return self.ty
