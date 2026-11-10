"""Context-free grammar model and a small text format for it.

Format (one rule group per line, the first left side is the axiom):

    S -> aAcc | b
    A -> eeAd | ε        # "eps" also means the empty string

A nonterminal is an uppercase letter followed by any number of digits or
primes (S, A, A′, A', Z12). Every other non-space character is a terminal.
Spaces inside a right side only separate symbols: "A 1" is A followed by 1.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

EPSILON = "ε"
ARROWS = ("->", "→", "::=")
_NONTERMINAL = re.compile(r"[A-Z][0-9'′]*")


class GrammarError(ValueError):
    """Raised for a grammar text that cannot be read."""

    def __init__(self, message: str, line: int | None = None):
        self.line = line
        super().__init__(f"рядок {line}: {message}" if line else message)


def is_nonterminal_token(token: str) -> bool:
    return bool(_NONTERMINAL.fullmatch(token))


def tokenize(text: str) -> list[str]:
    """Split a right side into symbols."""
    symbols, i = [], 0
    while i < len(text):
        if text[i].isspace():
            i += 1
            continue
        match = _NONTERMINAL.match(text, i)
        if match:
            symbols.append(match.group())
            i = match.end()
        else:
            symbols.append(text[i])
            i += 1
    return symbols


@dataclass
class Grammar:
    start: str
    rules: dict[str, list[tuple[str, ...]]] = field(default_factory=dict)

    @property
    def nonterminals(self) -> list[str]:
        seen = list(self.rules)
        for rhs_list in self.rules.values():
            for rhs in rhs_list:
                for symbol in rhs:
                    if is_nonterminal_token(symbol) and symbol not in seen:
                        seen.append(symbol)
        if self.start not in seen:
            seen.insert(0, self.start)
        return seen

    @property
    def terminals(self) -> list[str]:
        seen = []
        for rhs_list in self.rules.values():
            for rhs in rhs_list:
                for symbol in rhs:
                    if not is_nonterminal_token(symbol) and symbol not in seen:
                        seen.append(symbol)
        return seen

    def productions(self):
        for lhs, rhs_list in self.rules.items():
            for rhs in rhs_list:
                yield lhs, rhs

    def add(self, lhs: str, rhs: tuple[str, ...]) -> bool:
        """Add a rule unless it is already there. Returns True if added."""
        rhs_list = self.rules.setdefault(lhs, [])
        if rhs in rhs_list:
            return False
        rhs_list.append(rhs)
        return True

    def copy(self) -> Grammar:
        return Grammar(self.start, {lhs: list(rhs) for lhs, rhs in self.rules.items()})

    def __str__(self) -> str:
        lines = []
        for lhs in self.rules:
            if self.rules[lhs]:
                lines.append(f"{lhs} → " + " | ".join(format_rhs(r) for r in self.rules[lhs]))
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "start": self.start,
            "nonterminals": self.nonterminals,
            "terminals": self.terminals,
            "rules": [{"lhs": lhs, "rhs": list(rhs)} for lhs, rhs in self.productions()],
        }


def format_rhs(rhs: tuple[str, ...]) -> str:
    """Write a right side back as text, ε for the empty one."""
    if not rhs:
        return EPSILON
    out, previous = "", None
    for symbol in rhs:
        # a terminal digit or prime right after a nonterminal would merge with its name
        if previous and is_nonterminal_token(previous) and re.fullmatch(r"[0-9'′]", symbol):
            out += " "
        out += symbol
        previous = symbol
    return out


def parse_grammar(text: str) -> Grammar:
    """Read a grammar from the text format described in the module docstring."""
    grammar: Grammar | None = None
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        arrow = next((a for a in ARROWS if a in line), None)
        if arrow is None:
            raise GrammarError("немає стрілки ->, → або ::=", number)
        left, right = (part.strip() for part in line.split(arrow, 1))
        lhs = tokenize(left)
        if len(lhs) != 1 or not is_nonterminal_token(lhs[0]):
            raise GrammarError(
                f"ліва частина «{left}» має бути одним нетерміналом (КВ-граматика)", number
            )
        if grammar is None:
            grammar = Grammar(lhs[0])
        grammar.rules.setdefault(lhs[0], [])
        for alternative in right.split("|"):
            alternative = alternative.strip()
            if not alternative:
                raise GrammarError("порожня альтернатива, для ε пишіть ε або eps", number)
            rhs = () if alternative in (EPSILON, "eps") else tuple(tokenize(alternative))
            grammar.add(lhs[0], rhs)
    if grammar is None:
        raise GrammarError("граматика порожня")
    return grammar
