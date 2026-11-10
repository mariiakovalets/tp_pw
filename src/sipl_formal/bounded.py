"""Words of bounded length: helpers shared by the equation solver and the tests."""

from __future__ import annotations

from itertools import product

from .grammar import Grammar, is_nonterminal_token


def concat(left: set[str], right: set[str], max_len: int) -> set[str]:
    """Concatenation of two languages, keeping words of length ≤ max_len."""
    return {u + v for u in left for v in right if len(u) + len(v) <= max_len}


def all_words(alphabet: list[str], max_len: int) -> list[str]:
    """Every word over the alphabet of length ≤ max_len, shortest first."""
    return ["".join(p) for n in range(max_len + 1) for p in product(alphabet, repeat=n)]


def words_by_fixpoint(g: Grammar, max_len: int) -> set[str]:
    """Words of length ≤ max_len derived from the axiom: least fixpoint of the rules
    read as equations, starting from ∅. Works for any context-free grammar."""
    lang: dict[str, set[str]] = {a: set() for a in g.nonterminals}
    while True:
        new = {}
        for a in g.nonterminals:
            words = set()
            for rhs in g.rules.get(a, []):
                part = {""}
                for s in rhs:
                    part = concat(part, lang[s] if is_nonterminal_token(s) else {s}, max_len)
                words |= part
            new[a] = words
        if new == lang:
            return lang[g.start]
        lang = new


def words_by_derivation(g: Grammar, max_len: int) -> set[str]:
    """Terminal words of length ≤ max_len, found by searching sentential forms.

    Exact only for a grammar whose rules never shorten a form: no ε-rules
    except S → ε for an axiom that does not appear on the right, e.g. the
    result of normal_form.to_epsilon_free. Unit rules are fine.
    """
    words: set[str] = set()
    start: tuple[str, ...] = (g.start,)
    seen, todo = {start}, [start]
    if () in g.rules.get(g.start, []):
        words.add("")
    while todo:
        form = todo.pop()
        position = next((i for i, s in enumerate(form) if is_nonterminal_token(s)), None)
        if position is None:
            words.add("".join(form))
            continue
        for rhs in g.rules.get(form[position], []):
            if not rhs:
                continue
            new = form[:position] + rhs + form[position + 1 :]
            if len(new) <= max_len and new not in seen:
                seen.add(new)
                todo.append(new)
    return words
