SGR_CODES: dict[str, int] = {
    "bold": 1,
    "red": 31,
    "green": 32,
    "cyan": 36,
    "yellow": 33,
}

class Color:
    @staticmethod
    def format(style, string):
        if isinstance(style, str):
            names = [style]
        else:
            names = list(style)

        codes = [SGR_CODES[name] for name in names]
        return f"\x1b[{';'.join(str(c) for c in codes)}m{string}\x1b[0m"

