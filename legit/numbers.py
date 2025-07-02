class VarIntLE:
    @staticmethod
    def write(value: int) -> bytes:
        parts = []
        mask = 0xF
        shift = 4

        while value > mask:
            parts.append(0x80 | (value & mask))
            value >>= shift
            mask = 0x7F
            shift = 7

        parts.append(value)
        return bytes(parts)

    @staticmethod
    def read(stream) -> tuple[int, int]:
        first_b = stream.read(1)
        if not first_b:
            raise EOFError("Unexpected EOF while reading VarIntLE")
        first = first_b[0]

        value = first & 0xF
        shift = 4
        byte = first

        while byte & 0x80:
            nxt_b = stream.read(1)
            if not nxt_b:
                raise EOFError("Unexpected EOF while reading VarIntLE")
            byte = nxt_b[0]
            value |= (byte & 0x7F) << shift
            shift += 7

        return first, value

