from collections.abc import Sequence
from typing import Any

from beancount.core import data


class ReferenceDuplicatesComparator:
    def __init__(self, refs: Sequence[str] = ("ref",)) -> None:
        self.refs = refs

    def __call__(self, entry1: data.Directive, entry2: data.Directive) -> set[Any]:
        entry1Refs = set()
        entry2Refs = set()
        for ref in self.refs:
            if ref in entry1.meta:
                entry1Refs.add(entry1.meta[ref])
            if ref in entry2.meta:
                entry2Refs.add(entry2.meta[ref])

        return entry1Refs & entry2Refs
