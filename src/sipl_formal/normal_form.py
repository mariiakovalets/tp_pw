"""FORM-01: useless symbols, ε-rules, unit rules and Chomsky normal form.

Every transformation returns the new grammar together with a Step that says
in words what was done, so the whole chain can be printed as an explanation.
The order of steps follows practical work 4 of the course manual.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product

from .grammar import EPSILON, Grammar, format_rhs, is_nonterminal_token


@dataclass
class Step:
    title: str
    details: list[str] = field(default_factory=list)
    grammar: Grammar | None = None

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "details": self.details,
            "grammar": self.grammar.to_dict() if self.grammar else None,
            "grammar_text": str(self.grammar) if self.grammar else None,
        }


def _set(symbols) -> str:
    return "{" + ", ".join(symbols) + "}" if symbols else "∅"


def _rule(lhs: str, rhs: tuple[str, ...]) -> str:
    return f"{lhs} → {format_rhs(rhs)}"


def _fixpoint(first: list[str], grow) -> list[list[str]]:
    """Iterate a monotone set until it stops growing; returns every iteration."""
    iterations = [first]
    while True:
        current = iterations[-1]
        extra = [s for s in dict.fromkeys(grow(set(current))) if s not in current]
        if not extra:
            return iterations
        iterations.append(current + extra)


def productive_iterations(g: Grammar) -> list[list[str]]:
    """Pr0 = nonterminals with a rule of terminals only; Pr(i) adds those with a rule over Pr(i−1) ∪ T."""
    def ok(rhs, known):
        return all(not is_nonterminal_token(s) or s in known for s in rhs)

    first = [a for a in g.nonterminals if any(ok(r, set()) for r in g.rules.get(a, []))]
    return _fixpoint(first, lambda known: [a for a in g.nonterminals if any(ok(r, known) for r in g.rules.get(a, []))])


def reachable_iterations(g: Grammar) -> list[list[str]]:
    """R0 = {S}; R(i) adds nonterminals from right sides of rules of R(i−1)."""
    def grow(known):
        return [s for a in g.nonterminals if a in known for r in g.rules.get(a, []) for s in r if is_nonterminal_token(s)]

    return _fixpoint([g.start], grow)


def nullable_iterations(g: Grammar) -> list[list[str]]:
    """Nonterminals from which ε can be derived."""
    first = [a for a in g.nonterminals if () in g.rules.get(a, [])]
    return _fixpoint(
        first,
        lambda known: [a for a in g.nonterminals if any(r and all(s in known for s in r) for r in g.rules.get(a, []))],
    )


def remove_unproductive(g: Grammar) -> tuple[Grammar, Step]:
    iterations = productive_iterations(g)
    productive = set(iterations[-1])
    step = Step("Видалення непродуктивних нетерміналів")
    step.details += [f"Pr{i} = {_set(it)}" for i, it in enumerate(iterations)]
    step.details.append(f"Множина стабілізувалась: Pr = {_set(iterations[-1])}.")
    removed = [a for a in g.nonterminals if a not in productive]
    step.details.append(f"Непродуктивні: {_set(removed)}." if removed else "Непродуктивних нетерміналів немає.")
    new = Grammar(g.start)
    for lhs, rhs in g.productions():
        if lhs in productive and all(not is_nonterminal_token(s) or s in productive for s in rhs):
            new.add(lhs, rhs)
        else:
            step.details.append(f"видалено правило {_rule(lhs, rhs)}")
    new.rules.setdefault(g.start, [])
    if g.start not in productive:
        step.details.append("Аксіома непродуктивна, тому мова порожня.")
    step.grammar = new
    return new, step


def remove_unreachable(g: Grammar, title: str = "Видалення недосяжних нетерміналів") -> tuple[Grammar, Step]:
    iterations = reachable_iterations(g)
    reachable = set(iterations[-1])
    step = Step(title)
    step.details += [f"R{i} = {_set(it)}" for i, it in enumerate(iterations)]
    removed = [a for a in g.nonterminals if a not in reachable]
    step.details.append(f"Недосяжні: {_set(removed)}." if removed else "Недосяжних нетерміналів немає.")
    new = Grammar(g.start)
    for lhs, rhs in g.productions():
        if lhs in reachable:
            new.add(lhs, rhs)
        else:
            step.details.append(f"видалено правило {_rule(lhs, rhs)}")
    new.rules.setdefault(g.start, [])
    step.grammar = new
    return new, step


def remove_epsilon(g: Grammar) -> tuple[Grammar, Step]:
    iterations = nullable_iterations(g)
    nullable = set(iterations[-1])
    step = Step("Видалення ε-правил")
    step.details.append(f"ε-нетермінали (з них виводиться ε): {_set(iterations[-1])}.")
    new = Grammar(g.start)
    for lhs, rhs in g.productions():
        if not rhs:
            continue
        # every occurrence of a nullable nonterminal may be kept or dropped
        options = [((s,), ()) if s in nullable else ((s,),) for s in rhs]
        for choice in product(*options):
            variant = tuple(s for part in choice for s in part)
            if variant and variant != (lhs,) and new.add(lhs, variant) and variant != rhs:
                step.details.append(f"додано {_rule(lhs, variant)} (з {_rule(lhs, rhs)})")
    for lhs, rhs in g.productions():
        if not rhs:
            step.details.append(f"видалено правило {_rule(lhs, rhs)}")
    if g.start in nullable:
        new_start = fresh_name(new, g.start)
        rules = {new_start: [(g.start,), ()]}
        rules.update(new.rules)
        new = Grammar(new_start, rules)
        step.details.append(
            f"ε належить мові, тому введено нову аксіому {new_start}: {new_start} → {g.start} | {EPSILON}."
        )
    else:
        step.details.append(f"Аксіома {g.start} не є ε-нетерміналом, тому ε не належить мові.")
    new.rules.setdefault(new.start, [])
    step.grammar = new
    return new, step


def remove_unit(g: Grammar) -> tuple[Grammar, Step]:
    """Replace chains A → B with the non-unit rules of B."""
    step = Step("Видалення ланцюгових правил (A → B)")
    def is_unit(rhs):
        return len(rhs) == 1 and is_nonterminal_token(rhs[0])

    units = [(lhs, rhs) for lhs, rhs in g.productions() if is_unit(rhs)]
    if not units:
        step.details.append("Ланцюгових правил немає.")
        step.grammar = g.copy()
        return step.grammar, step
    new = Grammar(g.start)
    for a in g.nonterminals:
        closure, todo = [a], [a]
        while todo:
            b = todo.pop()
            for rhs in g.rules.get(b, []):
                if is_unit(rhs) and rhs[0] not in closure:
                    closure.append(rhs[0])
                    todo.append(rhs[0])
        for b in closure:
            for rhs in g.rules.get(b, []):
                if not is_unit(rhs) and new.add(a, rhs) and b != a:
                    step.details.append(f"додано {_rule(a, rhs)} (через {a} ⇒* {b})")
    for lhs, rhs in units:
        step.details.append(f"видалено правило {_rule(lhs, rhs)}")
    new.rules.setdefault(g.start, [])
    step.grammar = new
    return new, step


def fresh_name(g: Grammar, base: str | None = None, taken: set[str] | None = None) -> str:
    """A nonterminal name that is not used yet: base′, base″, … or a free letter, then Z1, Z2, …"""
    used = set(g.nonterminals) | (taken or set())
    if base:
        for primes in ("′", "′′", "′′′"):
            if base + primes not in used:
                return base + primes
    for letter in "DEFGHIJKLMNOPQRUVWXYZ":
        if letter not in used:
            return letter
    i = 1
    while f"Z{i}" in used:
        i += 1
    return f"Z{i}"


def replace_terminals(g: Grammar) -> tuple[Grammar, Step]:
    """In right sides of length ≥ 2 every terminal a becomes a new nonterminal with the rule → a."""
    step = Step("Заміна терміналів у довгих правилах новими нетерміналами")
    wrapper: dict[str, str] = {}
    new = Grammar(g.start)
    for lhs, rhs in g.productions():
        if len(rhs) < 2:
            new.add(lhs, rhs)
            continue
        out = []
        for s in rhs:
            if is_nonterminal_token(s):
                out.append(s)
                continue
            if s not in wrapper:
                base = s.upper() if s.isalpha() and s.isascii() else None
                wrapper[s] = fresh_name(g, base, taken=set(wrapper.values()) | set(new.rules))
                step.details.append(f"{wrapper[s]} → {s}")
            out.append(wrapper[s])
        new.add(lhs, tuple(out))
    for terminal, name in wrapper.items():
        new.add(name, (terminal,))
    if not wrapper:
        step.details.append("Терміналів у довгих правилах немає.")
    step.grammar = new
    return new, step


def split_long_rules(g: Grammar) -> tuple[Grammar, Step]:
    """A → X1 X2 … Xn (n > 2) becomes A → X1 N1, N1 → X2 N2, …; equal tails share one nonterminal."""
    step = Step("Розбиття правил, де справа більше двох нетерміналів")
    tail_name: dict[tuple[str, ...], str] = {}
    new = Grammar(g.start)
    for lhs, rhs in g.productions():
        if len(rhs) <= 2:
            new.add(lhs, rhs)
            continue
        parts, current = [], lhs
        rest = rhs
        while len(rest) > 2:
            tail = rest[1:]
            created = tail not in tail_name
            if created:
                tail_name[tail] = fresh_name(g, taken=set(tail_name.values()))
            parts.append(f"{current} → {format_rhs((rest[0], tail_name[tail]))}")
            new.add(current, (rest[0], tail_name[tail]))
            if not created:
                parts[-1] += f" ({tail_name[tail]} → … вже є)"
                break
            current, rest = tail_name[tail], tail
        else:
            new.add(current, rest)
            parts.append(f"{current} → {format_rhs(rest)}")
        step.details.append(f"{_rule(lhs, rhs)}: " + ", ".join(parts))
    if not step.details:
        step.details.append("Довгих правил немає.")
    step.grammar = new
    return new, step


def is_cnf(g: Grammar) -> bool:
    """Rules are A → BC, A → a, and S → ε only for an axiom that never appears on the right."""
    on_right = {s for _, rhs in g.productions() for s in rhs}
    for lhs, rhs in g.productions():
        if len(rhs) == 2 and all(is_nonterminal_token(s) for s in rhs):
            continue
        if len(rhs) == 1 and not is_nonterminal_token(rhs[0]):
            continue
        if not rhs and lhs == g.start and g.start not in on_right:
            continue
        return False
    return True


def reduce(g: Grammar) -> tuple[Grammar, list[Step]]:
    """Reduced grammar: no unproductive or unreachable nonterminals."""
    g1, s1 = remove_unproductive(g)
    g2, s2 = remove_unreachable(g1)
    return g2, [s1, s2]


def to_epsilon_free(g: Grammar) -> tuple[Grammar, list[Step]]:
    """Normal form without ε-rules (only S → ε for a new axiom if ε is in the language)."""
    g1, steps = reduce(g)
    g2, s3 = remove_epsilon(g1)
    return g2, steps + [s3]


def to_cnf(g: Grammar) -> tuple[Grammar, list[Step]]:
    g1, steps = to_epsilon_free(g)
    g2, s4 = remove_unit(g1)
    steps.append(s4)
    g3, s5 = remove_unreachable(g2, "Повторне видалення недосяжних нетерміналів")
    if any(line.startswith("видалено") for line in s5.details):
        steps.append(s5)
        g2 = g3
    g4, s6 = replace_terminals(g2)
    g5, s7 = split_long_rules(g4)
    steps += [s6, s7]
    return g5, steps


def steps_to_text(g: Grammar, steps: list[Step], result: Grammar, epsilon_free: bool = False) -> str:
    """The whole transformation as readable text: input, every step, result."""
    lines = ["Вхідна граматика:", str(g)]
    for i, step in enumerate(steps, start=1):
        lines += ["", f"Крок {i}. {step.title}"] + ["  " + line for line in step.details]
    title = "Нормальна форма без ε-правил" if epsilon_free else "Нормальна форма Хомського"
    return "\n".join(lines + ["", f"{title}:", str(result)])
