from collections.abc import Sequence

from beancount.core import data
from beancount.core.number import D
from beangulp import similar


class ReferenceDuplicatesComparator:
    """Compare entries by their reference metadata.

    If both entries carry a reference, they are duplicates when they share one.
    If at least one of them has no reference (e.g. a manually entered
    transaction or a statement without bank references), fall back to the
    beangulp heuristic: same accounts and exactly the same amounts.
    """

    def __init__(self, refs: Sequence[str] = ("ref",)) -> None:
        self.refs = refs
        # beangulp checks `ratio - 1 < epsilon`, so 0 would never match,
        # a tiny value only matches (practically) identical amounts.
        self.fallback = similar.heuristic_comparator(epsilon=D("0.000001"))

    def __call__(self, entry1: data.Directive, entry2: data.Directive) -> bool:
        entry1Refs = {entry1.meta[ref] for ref in self.refs if ref in entry1.meta}
        entry2Refs = {entry2.meta[ref] for ref in self.refs if ref in entry2.meta}

        if entry1Refs and entry2Refs:
            return bool(entry1Refs & entry2Refs)

        return self.fallback(entry1, entry2)
