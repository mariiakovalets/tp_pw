"""FORM-04: leftmost/rightmost derivations, derivation trees and ambiguity search.

The search is breadth-first over leftmost derivations, so it finds the
shortest derivations first. It is bounded by a depth and by a node budget;
the result says whether the search was complete within those bounds.
"""

from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field

from .grammar import EPSILON, Grammar, format_rhs, is_nonterminal_token


@dataclass
class Node:
    symbol: str
    children: list[Node] = field(default_factory=list)

    def leaves(self) -> str:
        if not self.children:
            return "" if self.symbol == EPSILON else self.symbol
        return "".join(child.leaves() for child in self.children)

    def to_dict(self) -> dict:
        return {"symbol": self.symbol, "children": [c.to_dict() for c in self.children]}


@dataclass
class Derivation:
    rules: list[tuple[str, tuple[str, ...]]]
    tree: Node
    leftmost: list[str]
    rightmost: list[str]

    def to_dict(self) -> dict:
        return {
            "rules": [f"{lhs} → {format_rhs(rhs)}" for lhs, rhs in self.rules],
            "leftmost": self.leftmost,
            "rightmost": self.rightmost,
            "tree": self.tree.to_dict(),
        }


@dataclass
class SearchResult:
    word: str
    derivations: list[Derivation]
    complete: bool
    max_depth: int

    @property
    def verdict(self) -> str:
        n = len(self.derivations)
        if n >= 2:
            return f"Знайдено різних дерев виводу: {n}. Граматика неоднозначна."
        if n == 1:
            if self.complete:
                return f"Слово має одне дерево виводу (у межах глибини {self.max_depth})."
            return "Знайдено одне дерево; пошук обірвано за лімітом, інших дерев не шукали до кінця."
        if self.complete:
            return f"Слово не виводиться за ≤ {self.max_depth} кроків."
        return "Виводу не знайдено, пошук обірвано за лімітом."

    def to_dict(self) -> dict:
        return {
            "word": self.word,
            "count": len(self.derivations),
            "complete": self.complete,
            "max_depth": self.max_depth,
            "verdict": self.verdict,
            "derivations": [d.to_dict() for d in self.derivations],
        }


def _form(symbols) -> str:
    return format_rhs(tuple(symbols)) if symbols else EPSILON


def tree_from_leftmost(start: str, rules: list[tuple[str, tuple[str, ...]]]) -> Node:
    """Replay a leftmost derivation and build its tree."""
    root = Node(start)
    frontier = [root]
    for lhs, rhs in rules:
        position = next(i for i, n in enumerate(frontier) if is_nonterminal_token(n.symbol) and not n.children)
        node = frontier[position]
        assert node.symbol == lhs
        node.children = [Node(s) for s in rhs] if rhs else [Node(EPSILON)]
        frontier[position : position + 1] = [c for c in node.children if c.symbol != EPSILON]
    return root


def derivation_from_tree(tree: Node, order: str = "left") -> list[str]:
    """The sentential forms of the leftmost or rightmost derivation that a tree describes."""
    frontier = [tree]
    forms = [_form(n.symbol for n in frontier)]
    while True:
        open_nodes = [i for i, n in enumerate(frontier) if n.children]
        if not open_nodes:
            return forms
        position = open_nodes[0] if order == "left" else open_nodes[-1]
        node = frontier[position]
        frontier[position : position + 1] = [c for c in node.children if c.symbol != EPSILON]
        forms.append(_form(n.symbol for n in frontier))


def find_derivations(
    g: Grammar, word: str, max_depth: int = 30, limit: int = 5, max_nodes: int = 200_000
) -> SearchResult:
    """Leftmost derivations of word, at most limit of them, each at most max_depth steps."""
    no_epsilon = all(rhs for _, rhs in g.productions())
    found: list[list[tuple[str, tuple[str, ...]]]] = []
    queue: deque[tuple[tuple[str, ...], list[tuple[str, tuple[str, ...]]]]] = deque([((g.start,), [])])
    visited = 0
    complete = True
    while queue:
        form, rules = queue.popleft()
        visited += 1
        if visited > max_nodes:
            complete = False
            break
        position = next((i for i, s in enumerate(form) if is_nonterminal_token(s)), None)
        if position is None:
            if "".join(form) == word:
                found.append(rules)
                if len(found) >= limit:
                    complete = not queue
                    break
            continue
        if "".join(form[:position]) != word[:position] or len(rules) >= max_depth:
            continue
        terminals = sum(1 for s in form if not is_nonterminal_token(s))
        if terminals > len(word) or (no_epsilon and len(form) > len(word)):
            continue
        for rhs in g.rules.get(form[position], []):
            queue.append((form[:position] + rhs + form[position + 1 :], rules + [(form[position], rhs)]))
    derivations = []
    for rules in found:
        tree = tree_from_leftmost(g.start, rules)
        derivations.append(Derivation(rules, tree, derivation_from_tree(tree, "left"), derivation_from_tree(tree, "right")))
    return SearchResult(word, derivations, complete, max_depth)


def tree_to_text(tree: Node) -> str:
    lines = [tree.symbol]

    def walk(node: Node, prefix: str) -> None:
        for i, child in enumerate(node.children):
            last = i == len(node.children) - 1
            lines.append(prefix + ("└─ " if last else "├─ ") + child.symbol)
            walk(child, prefix + ("   " if last else "│  "))

    walk(tree, "")
    return "\n".join(lines)


def result_to_text(result: SearchResult) -> str:
    parts = [f"Слово: {result.word or EPSILON}", result.verdict]
    for i, d in enumerate(result.derivations, start=1):
        parts.append(f"\n— Вивід {i} —")
        parts.append("Лівосторонній: " + " ⇒ ".join(d.leftmost))
        parts.append("Правосторонній: " + " ⇒ ".join(d.rightmost))
        parts.append("Дерево:\n" + tree_to_text(d.tree))
    return "\n".join(parts)


def result_to_dot(result: SearchResult) -> str:
    lines = ["digraph derivations {", "  node [shape=plaintext];"]
    counter = 0
    for i, d in enumerate(result.derivations, start=1):
        lines.append(f"  subgraph cluster_{i} {{")
        lines.append(f'    label="вивід {i}";')

        def walk(node: Node) -> str:
            nonlocal counter
            counter += 1
            name = f"n{counter}"
            shape = "ellipse" if is_nonterminal_token(node.symbol) else "box"
            lines.append(f'    {name} [label={json.dumps(node.symbol, ensure_ascii=False)}, shape={shape}];')
            for child in node.children:
                lines.append(f"    {name} -> {walk(child)};")
            return name

        walk(d.tree)
        lines.append("  }")
    lines.append("}")
    return "\n".join(lines)
