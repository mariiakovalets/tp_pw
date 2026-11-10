"""FORM-02: a grammar as a system of equations over languages, and its approximations.

Each nonterminal X becomes a variable, each rule X → α becomes a term of the
union on the right of X = …, and runs of terminals become one-word language
constants: S → aAcc gives S = {a}A{cc}. The least solution is found by
successive approximations from ∅ (practical work 5). Only words of length
≤ max_len are kept, so on that bound the approximations always stabilize.
"""

from __future__ import annotations

from dataclasses import dataclass

from .bounded import concat, words_by_derivation
from .grammar import EPSILON, Grammar, is_nonterminal_token
from .normal_form import to_epsilon_free

Item = tuple[str, str]  # ("const", word) or ("var", name)


@dataclass
class System:
    variables: list[str]
    equations: dict[str, list[list[Item]]]
    start: str

    def __str__(self) -> str:
        lines = []
        for x in self.variables:
            terms = [_term_text(t) for t in self.equations.get(x, [])] or ["∅"]
            lines.append(f"{x} = " + " ∪ ".join(terms))
        return "\n".join(lines)


def _term_text(term: list[Item]) -> str:
    return "".join("{" + (value or EPSILON) + "}" if kind == "const" else value for kind, value in term)


def build_system(g: Grammar) -> System:
    equations: dict[str, list[list[Item]]] = {}
    for lhs, rhs in g.productions():
        term: list[Item] = []
        for s in rhs:
            if is_nonterminal_token(s):
                term.append(("var", s))
            elif term and term[-1][0] == "const":
                term[-1] = ("const", term[-1][1] + s)
            else:
                term.append(("const", s))
        equations.setdefault(lhs, []).append(term or [("const", "")])
    return System(g.nonterminals, equations, g.start)


def apply(system: System, values: dict[str, set[str]], max_len: int) -> dict[str, set[str]]:
    """One approximation step: substitute the previous values into every right side."""
    result = {}
    for x in system.variables:
        words: set[str] = set()
        for term in system.equations.get(x, []):
            part = {""}
            for kind, value in term:
                part = concat(part, {value} if kind == "const" else values[value], max_len)
            words |= part
        result[x] = words
    return result


def approximations(system: System, max_len: int, max_steps: int = 100) -> list[dict[str, set[str]]]:
    """X0 = ∅, X(k+1) = φ(Xk) until nothing changes (or max_steps)."""
    steps: list[dict[str, set[str]]] = [{x: set() for x in system.variables}]
    while len(steps) <= max_steps:
        nxt = apply(system, steps[-1], max_len)
        if nxt == steps[-1]:
            break
        steps.append(nxt)
    return steps


def sort_words(words: set[str]) -> list[str]:
    return sorted(words, key=lambda w: (len(w), w))


def format_set(words: set[str], show: int = 12) -> str:
    if not words:
        return "∅"
    ordered = [w or EPSILON for w in sort_words(words)]
    text = ", ".join(ordered[:show])
    if len(ordered) > show:
        text += f", … (усього {len(ordered)})"
    return "{" + text + "}"


@dataclass
class Comparison:
    max_len: int
    from_equations: set[str]
    from_grammar: set[str]
    steps: int

    @property
    def equal(self) -> bool:
        return self.from_equations == self.from_grammar

    def to_dict(self) -> dict:
        return {
            "max_len": self.max_len,
            "equal": self.equal,
            "stabilized_after": self.steps,
            "from_equations": sort_words(self.from_equations),
            "from_grammar": sort_words(self.from_grammar),
            "only_in_equations": sort_words(self.from_equations - self.from_grammar),
            "only_in_grammar": sort_words(self.from_grammar - self.from_equations),
        }


def compare_with_grammar(g: Grammar, max_len: int) -> Comparison:
    """Solution of the system vs words found by derivations in the grammar (ε-free form)."""
    steps = approximations(build_system(g), max_len)
    free, _ = to_epsilon_free(g)
    return Comparison(max_len, steps[-1][g.start], words_by_derivation(free, max_len), len(steps) - 1)


def report(g: Grammar, max_len: int, show_steps: int = 5) -> str:
    system = build_system(g)
    steps = approximations(system, max_len)
    lines = ["Система рівнянь:", str(system), "", f"Наближення (слова довжини ≤ {max_len}):"]
    for k, values in enumerate(steps[: show_steps + 1]):
        lines.append(", ".join(f"{x}{k} = {format_set(values[x])}" for x in system.variables))
    if len(steps) - 1 > show_steps:
        lines.append(f"… усього {len(steps) - 1} кроків до стабілізації")
    else:
        lines.append(f"Стабілізація на кроці {len(steps) - 1} (на словах довжини ≤ {max_len}).")
    cmp = compare_with_grammar(g, max_len)
    lines += ["", f"Розв'язок для {g.start}: {format_set(cmp.from_equations)}"]
    if cmp.equal:
        lines.append(f"Збігається з мовою граматики на словах довжини ≤ {max_len}.")
    else:
        lines.append("НЕ збігається з мовою граматики:")
        lines.append(f"  лише в рівняннях: {format_set(cmp.from_equations - cmp.from_grammar)}")
        lines.append(f"  лише в граматиці: {format_set(cmp.from_grammar - cmp.from_equations)}")
    return "\n".join(lines)
