from legit.pack_stream import Stream
from legit.pack_reader import Reader


class RecvObjectsMixin:
    def recv_packet_objects(self, prefix: str = ''):
        stream = Stream(self.conn.input, prefix)
        reader = Reader(stream)

        reader.read_header()

        for n in reader.count:
            record, _ = stream.capture(lambda reader: reader.read_record())
            self.repo.database.store(record)

        stream.verify_checksum()
