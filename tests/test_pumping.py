import pytest

from sipl_formal.pumping import (
    PatternError,
    exploration_to_text,
    explore,
    parse_pattern,
    pump,
    split_by_lengths,
    split_to_text,
)

VARIANT_9 = "a e^{2n} b^n d^n c^{2n}"  # practical work 6, variant 9


def test_pattern_words_and_membership():
    lang = parse_pattern(VARIANT_9)
    assert lang.word(0) == "a"
    assert lang.word(1) == "aeebdcc"
    assert "aeeeebbddcccc" in lang
    assert "aeebbdcc" not in lang


def test_exponent_forms():
    lang = parse_pattern("a^(3n+1) b^2 c^n")
    assert lang.word(1) == "aaaabbc"
    assert str(lang) == "{ a^{3n+1} b^2 c^n | n ≥ 0 }"


@pytest.mark.parametrize("k", [3, 5, 7])
def test_non_cf_language_has_no_surviving_split(k):
    result = explore(parse_pattern(VARIANT_9), k=k, n=k)
    assert result.total > 0
    assert result.survivors == []
    assert "не виконується" in result.verdict


@pytest.mark.parametrize("pattern", ["a^n b^n", "a e^{2n} b d^n c^2"])
def test_context_free_languages_keep_surviving_splits(pattern):
    result = explore(parse_pattern(pattern), k=4, n=4)
    assert result.survivors
    assert all(s.survives for s in result.survivors)


def test_one_split_by_hand():
    lang = parse_pattern("a^n b^n")
    split = pump(lang, split_by_lengths("aabb", [1, 1, 0, 1]), i_max=2)
    assert split.marked() == "a[a][b]b"
    assert [w for _, w, _ in split.pumped] == ["ab", "aabb", "aaabbb"]
    assert split.survives
    assert "|t1t2| = 2 ≥ 1: так" in split_to_text(split, k=3)


def test_word_is_chosen_long_enough():
    result = explore(parse_pattern(VARIANT_9), k=10)
    assert len(result.word) >= 10 and result.n == 2


@pytest.mark.parametrize("text", ["a^{2m}", "a^", "", "a^{-n}"])
def test_bad_patterns_are_explained(text):
    with pytest.raises(PatternError):
        parse_pattern(text)


def test_text_contains_disclaimer():
    text = exploration_to_text(explore(parse_pattern("a^n b^n"), k=2))
    assert "асистент" in text and "[" in text
