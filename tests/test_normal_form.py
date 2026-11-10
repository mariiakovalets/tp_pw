from pathlib import Path

import pytest

from sipl_formal.bounded import all_words, words_by_derivation, words_by_fixpoint
from sipl_formal.cyk import cyk
from sipl_formal.grammar import parse_grammar
from sipl_formal.normal_form import (
    is_cnf,
    nullable_iterations,
    productive_iterations,
    reachable_iterations,
    to_cnf,
    to_epsilon_free,
)

EXAMPLES = Path(__file__).parent.parent / "examples" / "grammars"

# practical work 4: the worked example from the manual and variant 3
MANUAL_EXAMPLE = """
S -> AbCa | ABB | BScB | aSB
A -> Aa | eps
B -> bB | eps
C -> Dc | Cc | c
D -> Dd
"""
VARIANT_3 = """
S -> AbBC | ADcBC | ADCC | ACc
C -> eps | bCc
A -> eps | aA
B -> eps | bB
D -> dD
"""
OTHER = {
    "balanced, ε in language": "S -> aSbS | eps",
    "unit chain and cycle": "S -> A | a\nA -> B | b\nB -> A | SS",
    "unreachable only": "S -> ab\nX -> x",
    "empty language": "S -> aS",
    "long rule shares tails": "S -> abcd | bcd",
}


def test_productive_reachable_nullable_sets_match_the_manual():
    g = parse_grammar(MANUAL_EXAMPLE)
    assert productive_iterations(g)[-1] == ["A", "B", "C", "S"]
    assert [set(r) for r in reachable_iterations(g)] == [{"S"}, {"S", "A", "B", "C"}, {"S", "A", "B", "C", "D"}]
    assert set(nullable_iterations(g)[-1]) == {"A", "B", "S"}


def test_variant_3_epsilon_free_form_has_twelve_rules_for_s():
    g, steps = to_epsilon_free(parse_grammar(VARIANT_3))
    assert "D" not in g.nonterminals
    assert len(g.rules["S"]) == 12
    assert all(rhs for _, rhs in g.productions())
    assert any("не є ε-нетерміналом" in line for line in steps[-1].details)


@pytest.mark.parametrize("text", [MANUAL_EXAMPLE, VARIANT_3, *OTHER.values()])
def test_cnf_shape_and_same_language(text):
    g = parse_grammar(text)
    cnf, steps = to_cnf(g)
    assert is_cnf(cnf)
    assert all(step.details for step in steps)
    max_len = 7
    expected = words_by_fixpoint(g, max_len)
    alphabet = g.terminals or ["a"]
    assert {w for w in all_words(alphabet, max_len) if cyk(cnf, w)} == expected


@pytest.mark.parametrize("text", [MANUAL_EXAMPLE, VARIANT_3, *OTHER.values()])
def test_epsilon_free_form_keeps_the_language(text):
    g = parse_grammar(text)
    free, _ = to_epsilon_free(g)
    assert words_by_derivation(free, 8) == words_by_fixpoint(g, 8)


def test_new_axiom_when_epsilon_is_in_the_language():
    g, steps = to_cnf(parse_grammar("S -> aSbS | eps"))
    assert g.start == "S′"
    assert () in g.rules["S′"]
    assert any("нову аксіому" in line for s in steps for line in s.details)


def test_example_files_convert():
    for path in sorted(EXAMPLES.glob("*.cfg")):
        cnf, _ = to_cnf(parse_grammar(path.read_text(encoding="utf-8")))
        assert is_cnf(cnf), path.name
