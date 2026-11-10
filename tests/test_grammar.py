import pytest

from sipl_formal.grammar import GrammarError, format_rhs, parse_grammar, tokenize


def test_tokenize_splits_nonterminals_with_primes_and_digits():
    assert tokenize("AB′bZ12c") == ["A", "B′", "b", "Z12", "c"]
    assert tokenize("A 1") == ["A", "1"]


def test_parse_rules_epsilon_and_start():
    g = parse_grammar("S -> aAcc | b\nA → eeAd | ε\nB ::= eps  # comment")
    assert g.start == "S"
    assert g.rules["S"] == [("a", "A", "c", "c"), ("b",)]
    assert g.rules["A"] == [("e", "e", "A", "d"), ()]
    assert g.rules["B"] == [()]
    assert g.terminals == ["a", "c", "b", "e", "d"]


def test_str_round_trip():
    text = "S → aSb | ε"
    assert str(parse_grammar(text)) == text


def test_format_rhs_keeps_terminal_digit_apart():
    assert format_rhs(("A", "1")) == "A 1"
    assert parse_grammar("S -> A 1\nA -> a").rules["S"] == [("A", "1")]


@pytest.mark.parametrize(
    "text, message",
    [
        ("S aA", "немає стрілки"),
        ("aS -> a", "одним нетерміналом"),
        ("S -> a | ", "порожня альтернатива"),
        ("", "порожня"),
    ],
)
def test_errors_are_explained(text, message):
    with pytest.raises(GrammarError, match=message):
        parse_grammar(text)
