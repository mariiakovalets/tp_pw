"""Command line: sipl-formal <command> …  (exit code 0 = ok, 1 = bad input, 2 = bad arguments)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .derivation import find_derivations, result_to_dot, result_to_text
from .equations import build_system, compare_with_grammar, report
from .grammar import GrammarError, parse_grammar
from .normal_form import steps_to_text, to_cnf, to_epsilon_free
from .pumping import PatternError, exploration_to_text, explore, parse_pattern, pump, split_by_lengths, split_to_text
from .sipl import SiplSyntaxError, parse, tree_to_dot, tree_to_json, tree_to_text


def _read(path: str) -> str:
    return sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")


def _print_json(data) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_cnf(args) -> None:
    g = parse_grammar(_read(args.file))
    result, steps = to_epsilon_free(g) if args.epsilon_free else to_cnf(g)
    if args.json:
        _print_json({"input": g.to_dict(), "steps": [s.to_dict() for s in steps], "result": result.to_dict()})
        return
    print(steps_to_text(g, steps, result, epsilon_free=args.epsilon_free))


def cmd_derive(args) -> None:
    result = find_derivations(parse_grammar(_read(args.file)), args.word, args.depth, args.limit)
    if args.format == "json":
        _print_json(result.to_dict())
    elif args.format == "dot":
        print(result_to_dot(result))
    else:
        print(result_to_text(result))


def cmd_equations(args) -> None:
    g = parse_grammar(_read(args.file))
    if args.json:
        data = compare_with_grammar(g, args.max_len).to_dict()
        data["system"] = str(build_system(g))
        _print_json(data)
    else:
        print(report(g, args.max_len, args.steps))


def cmd_pump(args) -> None:
    lang = parse_pattern(args.pattern, args.n_min)
    if args.split:
        word = args.word or lang.word(args.n if args.n is not None else lang.n_min)
        lengths = [int(x) for x in args.split.split(",")]
        split = pump(lang, split_by_lengths(word, lengths), args.i_max)
        if args.json:
            _print_json(split.to_dict())
        else:
            print(f"Мова: L = {lang}\nСлово в мові: {'так' if word in lang else 'ні'}")
            print(split_to_text(split, args.k))
        return
    result = explore(lang, args.k, args.n, args.i_max)
    if args.json:
        _print_json(result.to_dict(args.show))
    else:
        print(exploration_to_text(result, args.show))


def cmd_sipl_check(args) -> None:
    parse(_read(args.file))
    print("Програма синтаксично правильна.")


def cmd_sipl_tree(args) -> None:
    tree = parse(_read(args.file))
    print({"json": tree_to_json, "dot": tree_to_dot}.get(args.format, tree_to_text)(tree))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sipl-formal", description="Інструменти з формальних мов для курсу ТП")
    parser.add_argument("--version", action="version", version=f"sipl-formal {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("cnf", help="FORM-01: зведення граматики і нормальна форма Хомського")
    p.add_argument("file", help="файл граматики (- для stdin)")
    p.add_argument("--epsilon-free", action="store_true", help="зупинитись на нормальній формі без ε-правил")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_cnf)

    p = sub.add_parser("derive", help="FORM-04: виводи та дерева виводу слова")
    p.add_argument("file")
    p.add_argument("word", help="слово з терміналів (\"\" для ε)")
    p.add_argument("--depth", type=int, default=30, help="найбільша кількість кроків виводу")
    p.add_argument("--limit", type=int, default=5, help="скільки різних виводів шукати")
    p.add_argument("--format", choices=["text", "json", "dot"], default="text")
    p.set_defaults(func=cmd_derive)

    p = sub.add_parser("equations", help="FORM-02: система рівнянь і наближення")
    p.add_argument("file")
    p.add_argument("--max-len", type=int, default=10, help="довжина слів, на якій рахуємо наближення")
    p.add_argument("--steps", type=int, default=5, help="скільки наближень показати")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_equations)

    p = sub.add_parser("pump", help="FORM-03: дослідження леми про накачку")
    p.add_argument("pattern", help='шаблон мови, наприклад "a e^{2n} b^n d^n c^{2n}"')
    p.add_argument("--k", type=int, required=True, help="число k з леми")
    p.add_argument("--n", type=int, help="взяти слово для цього n (інакше найкоротше з |t| ≥ k)")
    p.add_argument("--n-min", type=int, default=0, help="найменше n у мові")
    p.add_argument("--i-max", type=int, default=3, help="перевіряти i = 0 … i-max")
    p.add_argument("--split", help="один розклад: довжини |u|,|t1|,|x|,|t2|")
    p.add_argument("--word", help="слово для --split (за замовчуванням слово для --n)")
    p.add_argument("--show", type=int, default=3, help="скільки прикладів розкладів показати")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_pump)

    p = sub.add_parser("sipl-check", help="CORE-01: перевірити синтаксис SIPL-програми")
    p.add_argument("file")
    p.set_defaults(func=cmd_sipl_check)

    p = sub.add_parser("sipl-tree", help="VIS-01: дерево синтаксичного виводу SIPL-програми")
    p.add_argument("file")
    p.add_argument("--format", choices=["text", "json", "dot"], default="text")
    p.set_defaults(func=cmd_sipl_tree)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except (GrammarError, PatternError, SiplSyntaxError) as error:
        print(f"помилка: {error}", file=sys.stderr)
        return 1
    except FileNotFoundError as error:
        print(f"помилка: файл не знайдено: {error.filename}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
