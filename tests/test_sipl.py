import json
from pathlib import Path

import pytest

from sipl_formal.sipl import SiplSyntaxError, parse, tree_to_dot, tree_to_json, tree_to_text

SIPL = Path(__file__).parent.parent / "examples" / "sipl"
VALID = sorted((SIPL / "valid").glob("*.sipl"))
INVALID = sorted((SIPL / "invalid").glob("*.sipl"))


def test_there_are_enough_examples():
    assert len(VALID) >= 10 and len(INVALID) >= 10


@pytest.mark.parametrize("path", VALID, ids=lambda p: p.name)
def test_valid_programs_parse_and_leaves_spell_the_program(path):
    source = path.read_text(encoding="utf-8")
    tree = parse(source)
    assert tree.label == "<програма>"
    # reading the leaves left to right gives the program back (as in practical work 1)
    assert "".join(tree.leaves()) == "".join(source.split())


@pytest.mark.parametrize("path", INVALID, ids=lambda p: p.name)
def test_invalid_programs_report_line_and_column(path):
    with pytest.raises(SiplSyntaxError) as error:
        parse(path.read_text(encoding="utf-8"))
    assert error.value.line >= 1 and error.value.column >= 1
    assert "рядок" in str(error.value)


def test_error_position_points_at_the_problem():
    with pytest.raises(SiplSyntaxError) as error:
        parse((SIPL / "invalid" / "equals_instead_of_assign.sipl").read_text())
    assert (error.value.line, error.value.column) == (2, 5)


def test_priorities():
    tree = parse("begin R := 1 + 2 * 3 - 4 end")
    expr = tree.children[1].children[2]
    assert expr.rule == "sub" and expr.children[0].rule == "add"
    assert expr.children[0].children[2].rule == "mul"


def test_while_binds_tighter_than_sequence():
    stm = parse("begin while X > 0 do X := X - 1; Y := 1 end").children[1]
    assert stm.rule == "seq" and stm.children[0].rule == "while_stm"


def test_keyword_prefix_is_a_variable():
    assert parse("begin beginx := 1 end").children[1].children[0].text == "beginx"


def test_nodes_are_linked_to_source_fragments():
    source = (SIPL / "valid" / "power.sipl").read_text()
    tree = parse(source)

    def check(node):
        assert source[node.span.start : node.span.end] == node.text
        for child in node.children:
            check(child)

    check(tree)


def test_exports():
    tree = parse((SIPL / "valid" / "power.sipl").read_text())
    data = json.loads(tree_to_json(tree))
    assert data["label"] == "<програма>" and data["span"]["line"] == 1
    dot = tree_to_dot(tree)
    assert dot.startswith("digraph") and "tooltip" in dot
    assert "«R := R * X»" in tree_to_text(tree)
