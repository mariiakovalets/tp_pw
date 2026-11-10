import json

from sipl_formal.derivation import find_derivations, result_to_dot, result_to_text
from sipl_formal.grammar import parse_grammar

ARITHMETIC = "E -> E+E | E*E | (E) | x"
# example 4.26 from the lecture on ambiguous grammars
WITH_EPSILON = """
S -> AB | CD | eps
A -> eps | aA
B -> eps | bBc
C -> eps | aCb
D -> eps | cD
"""


def test_ambiguous_word_has_two_trees():
    result = find_derivations(parse_grammar(ARITHMETIC), "x+x*x")
    assert len(result.derivations) == 2
    assert "неоднозначна" in result.verdict
    for d in result.derivations:
        assert d.tree.leaves() == "x+x*x"
        assert d.leftmost[-1] == d.rightmost[-1] == "x+x*x"
        assert len(d.leftmost) == len(d.rightmost)


def test_unambiguous_word_with_complete_search():
    result = find_derivations(parse_grammar("S -> aSb | eps"), "aabb")
    assert len(result.derivations) == 1
    assert result.complete
    assert result.derivations[0].leftmost == ["S", "aSb", "aaSbb", "aabb"]


def test_grammar_with_epsilon_rules_finds_both_trees():
    result = find_derivations(parse_grammar(WITH_EPSILON), "aabbcc", max_depth=12)
    assert len(result.derivations) == 2


def test_rightmost_differs_from_leftmost():
    d = find_derivations(parse_grammar("S -> AB\nA -> a\nB -> b"), "ab").derivations[0]
    assert d.leftmost == ["S", "AB", "aB", "ab"]
    assert d.rightmost == ["S", "AB", "Ab", "ab"]


def test_word_not_in_language():
    result = find_derivations(parse_grammar("S -> aSb | eps"), "aab", max_depth=10)
    assert result.derivations == []
    assert "не виводиться" in result.verdict


def test_exports():
    result = find_derivations(parse_grammar(ARITHMETIC), "x+x*x")
    data = json.loads(json.dumps(result.to_dict(), ensure_ascii=False))
    assert data["count"] == 2 and data["derivations"][0]["tree"]["symbol"] == "E"
    dot = result_to_dot(result)
    assert dot.startswith("digraph") and "cluster_2" in dot
    assert "└─" in result_to_text(result)
