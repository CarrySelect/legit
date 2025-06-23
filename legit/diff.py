from legit.myers import Edit, Myers


def lines(document: str | list[str]) -> list[str]:
    if isinstance(document, str):
        return document.splitlines()
    else:
        return document


def diff(a: str | list[str], b: str | list[str]) -> list[Edit]:
    return Myers.diff(lines(a), lines(b))
