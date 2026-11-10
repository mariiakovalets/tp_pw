"""Parse SIPL programs and export the parse (derivation) tree.

Every node keeps its source span and the fragment of the program it covers,
so the tree can be matched with the text.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from importlib.resources import files

from lark import Lark, Token, Tree
from lark.exceptions import UnexpectedCharacters, UnexpectedEOF, UnexpectedInput, UnexpectedToken

# rule name -> syntactic category of the course BNF
CATEGORY = {
    "program": "<програма>",
    "seq": "<оператор>", "assign": "<оператор>", "if_stm": "<оператор>",
    "while_stm": "<оператор>", "block": "<оператор>", "skip": "<оператор>",
    "add": "<вираз>", "sub": "<вираз>", "mul": "<вираз>", "paren_a": "<вираз>",
    "or_b": "<умова>", "not_b": "<умова>", "eq": "<умова>", "gt": "<умова>", "paren_b": "<умова>",
    "var": "<змінна>", "num": "<число>",
}

READABLE = {
    "BEGIN": "begin", "END": "end", "IF": "if", "THEN": "then", "ELSE": "else",
    "WHILE": "while", "DO": "do", "SKIP": "skip", "OR": "or", "NOT": "not",
    "ASSIGN": ":=", "SEMI": ";", "PLUS": "+", "MINUS": "-", "TIMES": "*",
    "EQ": "=", "GT": ">", "LPAR": "(", "RPAR": ")", "VAR": "змінна", "NUM": "число",
    "$END": "кінець тексту",
}

_parser: Lark | None = None


def _get_parser() -> Lark:
    global _parser
    if _parser is None:
        grammar = files("sipl_formal.sipl").joinpath("sipl.lark").read_text(encoding="utf-8")
        _parser = Lark(grammar, start="program", parser="lalr", propagate_positions=True, keep_all_tokens=True)
    return _parser


class SiplSyntaxError(ValueError):
    def __init__(self, message: str, line: int, column: int):
        self.line, self.column = line, column
        super().__init__(f"рядок {line}, стовпчик {column}: {message}")


@dataclass
class Span:
    line: int
    column: int
    end_line: int
    end_column: int
    start: int
    end: int

    def __str__(self) -> str:
        return f"{self.line}:{self.column}–{self.end_line}:{self.end_column}"


@dataclass
class ParseNode:
    rule: str  # Lark rule name, or token type for leaves
    label: str  # course category for inner nodes, token text for leaves
    span: Span
    text: str  # source fragment
    children: list[ParseNode] = field(default_factory=list)

    @property
    def is_leaf(self) -> bool:
        return not self.children

    def leaves(self) -> list[str]:
        return [self.label] if self.is_leaf else [w for c in self.children for w in c.leaves()]

    def to_dict(self) -> dict:
        d: dict = {"rule": self.rule, "label": self.label, "span": vars(self.span), "text": self.text}
        if self.children:
            d["children"] = [c.to_dict() for c in self.children]
        return d


def _expected(names) -> str:
    return ", ".join(sorted({READABLE.get(n, n) for n in names}))


def _convert(node: Tree | Token, source: str) -> ParseNode:
    if isinstance(node, Token):
        span = Span(
            node.line or 0, node.column or 0, node.end_line or 0, node.end_column or 0,
            node.start_pos or 0, node.end_pos or 0,
        )
        return ParseNode(node.type, str(node), span, str(node))
    meta = node.meta
    span = Span(meta.line, meta.column, meta.end_line, meta.end_column, meta.start_pos, meta.end_pos)
    children = [_convert(c, source) for c in node.children]
    return ParseNode(node.data, CATEGORY.get(node.data, node.data), span, source[span.start : span.end], children)


def parse(source: str) -> ParseNode:
    """Parse a SIPL program; raises SiplSyntaxError with line and column."""
    try:
        tree = _get_parser().parse(source)
    except UnexpectedCharacters as e:
        char = source[e.pos_in_stream] if e.pos_in_stream is not None else "?"
        raise SiplSyntaxError(f"неочікуваний символ «{char}»", e.line, e.column) from None
    except UnexpectedToken as e:
        # accepts is the exact set for this parser state; expected may include extra lookaheads
        e.expected = e.accepts or e.expected
        if e.token.type == "$END":
            line = source.count("\n") + 1
            column = len(source.rsplit("\n", 1)[-1]) + 1
            raise SiplSyntaxError(f"програма обривається, очікувалось: {_expected(e.expected)}", line, column) from None
        raise SiplSyntaxError(
            f"неочікуване «{e.token}», очікувалось: {_expected(e.expected)}", e.line, e.column
        ) from None
    except UnexpectedEOF as e:
        line = source.count("\n") + 1
        raise SiplSyntaxError(f"програма обривається, очікувалось: {_expected(e.expected)}", line, 1) from None
    except UnexpectedInput as e:  # pragma: no cover - other lark errors
        raise SiplSyntaxError(str(e), getattr(e, "line", 1), getattr(e, "column", 1)) from None
    return _convert(tree, source)


def tree_to_text(root: ParseNode) -> str:
    lines = [f"{root.label}  [{root.span}]"]

    def walk(node: ParseNode, prefix: str) -> None:
        for i, child in enumerate(node.children):
            last = i == len(node.children) - 1
            tail = f"  [{child.span}]" if child.is_leaf else f"  [{child.span}] «{' '.join(child.text.split())}»"
            lines.append(prefix + ("└─ " if last else "├─ ") + child.label + tail)
            walk(child, prefix + ("   " if last else "│  "))

    walk(root, "")
    return "\n".join(lines)


def tree_to_json(root: ParseNode) -> str:
    return json.dumps(root.to_dict(), ensure_ascii=False, indent=2)


def tree_to_dot(root: ParseNode) -> str:
    lines = ["digraph parse_tree {", "  node [fontname=Helvetica];"]
    counter = 0

    def walk(node: ParseNode) -> str:
        nonlocal counter
        counter += 1
        name = f"n{counter}"
        shape = "box" if node.is_leaf else "ellipse"
        tooltip = f"{node.span}: {' '.join(node.text.split())}"
        lines.append(
            f"  {name} [label={json.dumps(node.label, ensure_ascii=False)}, shape={shape}, "
            f"tooltip={json.dumps(tooltip, ensure_ascii=False)}];"
        )
        for child in node.children:
            lines.append(f"  {name} -> {walk(child)};")
        return name

    walk(root)
    lines.append("}")
    return "\n".join(lines)
