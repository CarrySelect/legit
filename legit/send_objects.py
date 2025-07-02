from legit.rev_list import RevList
from legit.pack_writer import Writer


class SendObjectsMixin:
    def send_packet_objects(self, revs):
        rev_opts = { "objects": True, "missing": True }
        rev_list = RevList(self.repo, revs, rev_opts)

        pack_compression = self.repo.config.get(["pack", "compression"]) or self.repo.config.get(["core", "compression"])

        write_opts = {"compression": pack_compression}
        writer = Writer(self.conn.output, self.repo.database, write_opts)

        writer.write_objects(rev_list)
