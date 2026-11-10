from pathlib import Path

import pytest

from sipl_formal.equations import approximations, build_system, compare_with_grammar, report
from sipl_formal.grammar import parse_grammar

EXAMPLES = Path(__file__).parent.parent / "examples" / "grammars"
VARIANT_9 = "S -> aAcc\nA -> eeAd | b"


def test_system_is_written_like_in_the_manual():
    assert str(build_system(parse_grammar(VARIANT_9))) == "S = {a}A{cc}\nA = {ee}A{d} ∪ {b}"
    assert str(build_system(parse_grammar("S -> aSb | eps"))) == "S = {a}S{b} ∪ {ε}"


def test_variant_9_approximations_follow_the_induction_claim():
    steps = approximations(build_system(parse_grammar(VARIANT_9)), max_len=40)
    for k in range(6):
        assert steps[k]["A"] == {"e" * (2 * i) + "b" + "d" * i for i in range(k)}
        assert steps[k]["S"] == {"a" + "e" * (2 * i) + "b" + "d" * i + "cc" for i in range(k - 1)}


def test_anbn_first_approximations():
    steps = approximations(build_system(parse_grammar("S -> aSb | eps")), max_len=10)
    assert [steps[k]["S"] for k in range(4)] == [set(), {""}, {"", "ab"}, {"", "ab", "aabb"}]


@pytest.mark.parametrize("path", sorted(EXAMPLES.glob("*.cfg")), ids=lambda p: p.name)
def test_solution_matches_the_grammar(path):
    cmp = compare_with_grammar(parse_grammar(path.read_text(encoding="utf-8")), max_len=8)
    assert cmp.equal, cmp.to_dict()


def test_empty_language():
    cmp = compare_with_grammar(parse_grammar("S -> aS"), max_len=6)
    assert cmp.equal and cmp.from_equations == set()


def test_report_text():
    text = report(parse_grammar(VARIANT_9), max_len=12)
    assert "S0 = ∅" in text and "Збігається" in text
