from legit.pack_stream import Stream
from legit.pack_reader import Reader


class RecvObjectsMixin:
    def recv_packed_objects(self, prefix: str = ''):
        stream = Stream(self.conn.input, prefix)
        reader = Reader(stream)

        reader.read_header()

        for n in range(reader.count):
            with stream.capture():
                record = reader.read_record()
            if record is not None:
                self.repo.database.store(record)

        stream.verify_checksum()
