"""CYK membership test for a grammar in Chomsky normal form."""

from __future__ import annotations

from .grammar import Grammar


def cyk(g: Grammar, word: str) -> bool:
    """True if the CNF grammar g derives word (a string of one-character terminals)."""
    if word == "":
        return () in g.rules.get(g.start, [])
    n = len(word)
    # table[i][l] = nonterminals deriving word[i:i+l+1]
    table: list[list[set[str]]] = [[set() for _ in range(n)] for _ in range(n)]
    for i, ch in enumerate(word):
        table[i][0] = {lhs for lhs, rhs in g.productions() if rhs == (ch,)}
    pairs = [(lhs, rhs) for lhs, rhs in g.productions() if len(rhs) == 2]
    for length in range(2, n + 1):
        for i in range(n - length + 1):
            cell = table[i][length - 1]
            for split in range(1, length):
                left, right = table[i][split - 1], table[i + split][length - split - 1]
                for lhs, (b, c) in pairs:
                    if b in left and c in right:
                        cell.add(lhs)
    return g.start in table[0][n - 1]
