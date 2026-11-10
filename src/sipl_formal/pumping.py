"""FORM-03: Pumping Lemma Explorer.

An assistant, not a decision procedure. For a language given by a pattern
with one parameter n (blocks like e^{2n}, b^n, c^2) it takes one word and
one value of k, lists every split t = u·t1·x·t2·v with |t1t2| ≥ 1 and
|t1xt2| ≤ k, and checks whether u·t1^i·x·t2^i·v stays in the language for
i = 0 … i_max. If no split survives, the lemma fails for this word and k,
which is what a proof that L is not context-free has to show for every k.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_BLOCK = re.compile(r"\s*([^\s^])(?:\^(\{[^}]*\}|\([^)]*\)|[0-9]*n|[0-9]+))?")
_LINEAR = re.compile(r"^(?:(\d*)n)?\s*(?:([+-])\s*(\d+))?$|^(\d+)$")

DISCLAIMER = (
    "Це асистент, а не універсальний вирішувач: перевірено лише одне слово, одне k "
    "і скінченну кількість значень i. Щоб довести, що мова не КВ, міркування має "
    "працювати для довільного k."
)


class PatternError(ValueError):
    pass


@dataclass(frozen=True)
class Block:
    letter: str
    coef: int  # length of the block is coef·n + const
    const: int

    def length(self, n: int) -> int:
        return self.coef * n + self.const

    def __str__(self) -> str:
        if self.coef == 0:
            return self.letter if self.const == 1 else f"{self.letter}^{self.const}"
        exp = ("" if self.coef == 1 else str(self.coef)) + "n"
        if self.const:
            exp += f"{self.const:+d}"
        return f"{self.letter}^{{{exp}}}" if len(exp) > 1 else f"{self.letter}^{exp}"


@dataclass
class PatternLanguage:
    blocks: list[Block]
    n_min: int = 0

    def word(self, n: int) -> str:
        return "".join(b.letter * b.length(n) for b in self.blocks)

    def __contains__(self, w: str) -> bool:
        n = self.n_min
        while True:
            candidate = self.word(n)
            if candidate == w:
                return True
            if len(candidate) > len(w) or all(b.coef == 0 for b in self.blocks):
                return False
            n += 1

    def __str__(self) -> str:
        return "{ " + " ".join(str(b) for b in self.blocks) + f" | n ≥ {self.n_min} }}"


def _parse_exponent(text: str) -> tuple[int, int]:
    text = text.strip("{}()").replace(" ", "")
    match = _LINEAR.match(text)
    if not match or not text:
        raise PatternError(f"не вдалося прочитати показник «{text}»: очікується, наприклад, 2n, n, 3n+1 або 2")
    if match.group(4) is not None:
        return 0, int(match.group(4))
    coef = int(match.group(1)) if match.group(1) else 1
    const = int(match.group(3)) * (-1 if match.group(2) == "-" else 1) if match.group(3) else 0
    return coef, const


def parse_pattern(text: str, n_min: int = 0) -> PatternLanguage:
    """Read a pattern such as "a e^{2n} b^n d^n c^{2n}"."""
    blocks, pos = [], 0
    text = text.strip()
    while pos < len(text):
        match = _BLOCK.match(text, pos)
        if not match or match.end() == pos:
            raise PatternError(f"не вдалося прочитати шаблон з позиції {pos + 1}: «{text[pos:]}»")
        letter, exponent = match.group(1), match.group(2)
        coef, const = _parse_exponent(exponent) if exponent else (0, 1)
        if coef < 0 or coef * n_min + const < 0:
            raise PatternError(f"блок {letter}^{exponent} має від'ємну довжину")
        blocks.append(Block(letter, coef, const))
        pos = match.end()
        while pos < len(text) and text[pos].isspace():
            pos += 1
    if not blocks:
        raise PatternError("шаблон порожній")
    return PatternLanguage(blocks, n_min)


@dataclass
class Split:
    u: str
    t1: str
    x: str
    t2: str
    v: str
    pumped: list[tuple[int, str, bool]] = field(default_factory=list)

    @property
    def survives(self) -> bool:
        return all(ok for _, _, ok in self.pumped)

    @property
    def first_failure(self) -> int | None:
        return next((i for i, _, ok in self.pumped if not ok), None)

    def marked(self) -> str:
        return f"{self.u}[{self.t1}]{self.x}[{self.t2}]{self.v}"

    def to_dict(self) -> dict:
        return {
            "u": self.u, "t1": self.t1, "x": self.x, "t2": self.t2, "v": self.v,
            "survives": self.survives,
            "pumped": [{"i": i, "word": w, "in_language": ok} for i, w, ok in self.pumped],
        }


def pump(lang: PatternLanguage, split: Split, i_max: int) -> Split:
    split.pumped = []
    for i in range(i_max + 1):
        w = split.u + split.t1 * i + split.x + split.t2 * i + split.v
        split.pumped.append((i, w, w in lang))
    return split


def split_by_lengths(word: str, lengths: list[int]) -> Split:
    """Split word by the lengths of u, t1, x, t2 (v is the rest)."""
    if len(lengths) != 4 or any(n < 0 for n in lengths) or sum(lengths) > len(word):
        raise PatternError("потрібно чотири невід'ємні довжини |u|,|t1|,|x|,|t2| із сумою ≤ |t|")
    a, b, c, d = lengths
    return Split(word[:a], word[a : a + b], word[a + b : a + b + c], word[a + b + c : a + b + c + d], word[a + b + c + d :])


def all_splits(word: str, k: int):
    for start in range(len(word)):
        for l1 in range(k + 1):
            for lx in range(k + 1 - l1):
                for l2 in range(k + 1 - l1 - lx):
                    if l1 + l2 == 0 or start + l1 + lx + l2 > len(word):
                        continue
                    yield split_by_lengths(word, [start, l1, lx, l2])


@dataclass
class Exploration:
    language: PatternLanguage
    word: str
    n: int | None
    k: int
    i_max: int
    total: int
    survivors: list[Split]
    failed: list[Split]

    @property
    def verdict(self) -> str:
        if self.survivors:
            return (
                f"Знайдено {len(self.survivors)} розклад(ів), що витримують накачку для i = 0…{self.i_max}. "
                "Для цього слова й k лему не спростовано."
            )
        return (
            f"Жоден із {self.total} розкладів не витримує накачки: для кожного є i ≤ {self.i_max}, "
            "при якому слово виходить за межі мови. Для цього слова й k лема не виконується."
        )

    def to_dict(self, show: int = 10) -> dict:
        return {
            "language": str(self.language), "word": self.word, "n": self.n, "k": self.k,
            "i_max": self.i_max, "splits_checked": self.total,
            "surviving": len(self.survivors), "verdict": self.verdict, "note": DISCLAIMER,
            "surviving_examples": [s.to_dict() for s in self.survivors[:show]],
            "failing_examples": [s.to_dict() for s in self.failed[:show]],
        }


def choose_word(lang: PatternLanguage, k: int, n: int | None = None) -> tuple[str, int]:
    """The word for the given n, or the shortest word of length ≥ k."""
    if n is not None:
        if n < lang.n_min:
            raise PatternError(f"n має бути ≥ {lang.n_min}")
        return lang.word(n), n
    n = lang.n_min
    while len(lang.word(n)) < k:
        if all(b.coef == 0 for b in lang.blocks):
            raise PatternError("мова скінченна: немає слів довжини ≥ k")
        n += 1
    return lang.word(n), n


def explore(lang: PatternLanguage, k: int, n: int | None = None, i_max: int = 3) -> Exploration:
    if k < 1:
        raise PatternError("k має бути ≥ 1")
    word, n = choose_word(lang, k, n)
    survivors: list[Split] = []
    failed: list[Split] = []
    total = 0
    for split in all_splits(word, k):
        total += 1
        pump(lang, split, i_max)
        (survivors if split.survives else failed).append(split)
    return Exploration(lang, word, n, k, i_max, total, survivors, failed)


def split_to_text(split: Split, k: int | None = None) -> str:
    lines = [f"t = u[t1]x[t2]v = {split.marked()}"]
    lines.append(f"u = «{split.u}», t1 = «{split.t1}», x = «{split.x}», t2 = «{split.t2}», v = «{split.v}»")
    ok1 = len(split.t1 + split.t2) >= 1
    lines.append(f"|t1t2| = {len(split.t1 + split.t2)} ≥ 1: {'так' if ok1 else 'ні'}")
    if k is not None:
        size = len(split.t1 + split.x + split.t2)
        lines.append(f"|t1xt2| = {size} ≤ k = {k}: {'так' if size <= k else 'ні'}")
    for i, w, ok in split.pumped:
        lines.append(f"  i = {i}: {w or 'ε'}  {'∈ L' if ok else '∉ L'}")
    return "\n".join(lines)


def exploration_to_text(result: Exploration, show: int = 3) -> str:
    lines = [
        f"Мова: L = {result.language}",
        f"Слово: t = {result.word} (n = {result.n}, |t| = {len(result.word)}), k = {result.k}",
        f"Перевірено розкладів: {result.total}; i = 0…{result.i_max}",
        result.verdict,
    ]
    if result.survivors:
        lines.append("\nРозклади, що витримують накачку:")
        lines += [split_to_text(s, result.k) for s in result.survivors[:show]]
    if result.failed:
        lines.append("\nПриклади розкладів, що не витримують:")
        lines += [split_to_text(s, result.k) for s in result.failed[:show]]
    lines += ["", DISCLAIMER]
    return "\n".join(lines)
