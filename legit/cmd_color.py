SGR_CODES: dict[str, int] = {
    "bold": 1,
    "red": 31,
    "green": 32,
    "cyan": 36,
    "yellow": 33,
}

class Color:
    @staticmethod
    def format(color: str, msg: str) -> str:
        code = SGR_CODES.get(color)
        if code is None:
            return msg
        return f"\033[{code}m{msg}\033[0m"





