import io
import zlib
import struct

from legit.pack import InvalidPack, HEADER_SIZE, HEADER_FORMAT, SIGNATURE, VERSION, TYPE_CODES, COMMIT, BLOB, TREE, Record
from legit.numbers import VarIntLE


TYPE_CODES_REVERSED = {
    COMMIT: "commit",
    BLOB: "blob",
    TREE: "tree"
}


class Reader:
    def __init__(self, f):
        self.input = f
        self.count = 0

    def read_header(self):
        data = self.input.read(HEADER_SIZE)
        signature, version, self.count = struct.unpack(HEADER_FORMAT, data)

        if signature != SIGNATURE:
            raise InvalidPack(f"bad pack signature: {signature}")

        if version != VERSION:
            raise InvalidPack(f"unsupported pack version: {version}")

    def read_record(self) -> Record:
        ty, _ = self.read_record_header()
        return Record(TYPE_CODES_REVERSED[ty], self.read_zlib_stream())

    def read_record_header(self):
        byte, size = VarIntLE.read(self.input)
        ty = (byte >> 4) & 0x7
        return ty, size

    def read_zlib_stream(self) -> bytes:
        decompressor = zlib.decompressobj()
        output = bytearray()
    
        while True:
            chunk = self.input.read_nonblock(256)
            if not chunk:
                raise InvalidPack("Unexpected EOF in zlib stream")
            
            output.extend(decompressor.decompress(chunk))
    
            if decompressor.eof:
                leftover = decompressor.unused_data
                if leftover:
                    self.input.seek(-len(leftover), io.SEEK_CUR)
                break
    
        return bytes(output)


