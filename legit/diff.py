from typing import Union, List
from legit.myers import Edit, Line, Myers


def lines(document: Union[str, List[str]]) -> List[Line]:
    """
    Turn a string or list of strings into a list of Line objects,
    numbering from 1.
    """
    if isinstance(document, str):
        doc_lines = document.splitlines(keepends=True)
    else:
        doc_lines = document
    return [Line(i + 1, text) for i, text in enumerate(doc_lines)]

def diff(a: Union[str, List[str]], b: Union[str, List[str]]) -> List[Edit]:
    """
    Compute the diff between a and b, returning a list of Edit objects.
    """
    return Myers.diff(lines(a), lines(b))


