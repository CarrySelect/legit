from legit.cmd_base import Base


class UploadPack(Base):
    def run(self) -> None:
        self.accept_client("upload-pack")

        self.send_references()
        self.recv_want_list()
        self.recv_have_list()

        self.send_objects()

        self.exit(0)

    def recv_want_list(self):
        self.wanted = self.recv_oids("want", None)
        if not self.wanted:
            self.exit(0)

    def recv_oids(self, prefix, terminator):
        pattern = f"^{prefix} ([0-9a-f]+)$"
        result = set()

        for line in self.conn.recv_until(terminator):
            result.add(pattern.match(line).group(1))

        return result

    def recv_have_list(self):
        self.remote_has = self.recv_oids("have", "done")
        self.conn.send_packet("NAK")

    def send_objects(self):
        revs = self.wanted + set(f"^{oid}" for oid in self.remote_has)
        self.send_packet_objects(revs)


    
