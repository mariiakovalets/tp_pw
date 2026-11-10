import json
from pathlib import Path

import pytest

from sipl_formal.cli import main

EX = Path(__file__).parent.parent / "examples"


def run(capsys, *args):
    code = main([str(a) for a in args])
    out = capsys.readouterr()
    return code, out.out, out.err


def test_cnf_text_and_json(capsys):
    code, out, _ = run(capsys, "cnf", EX / "grammars" / "pr4_variant3.cfg")
    assert code == 0 and "Нормальна форма Хомського" in out and "Pr0" in out
    code, out, _ = run(capsys, "cnf", EX / "grammars" / "pr4_variant3.cfg", "--json")
    assert code == 0 and json.loads(out)["steps"][0]["title"].startswith("Видалення")


def test_epsilon_free_only(capsys):
    code, out, _ = run(capsys, "cnf", EX / "grammars" / "pr4_variant3.cfg", "--epsilon-free")
    assert code == 0 and "без ε-правил" in out


def test_derive_formats(capsys):
    g = EX / "grammars" / "arithmetic_ambiguous.cfg"
    assert run(capsys, "derive", g, "x+x*x")[1].count("— Вивід") == 2
    assert json.loads(run(capsys, "derive", g, "x+x*x", "--format", "json")[1])["count"] == 2
    assert run(capsys, "derive", g, "x", "--format", "dot")[1].startswith("digraph")


def test_equations(capsys):
    code, out, _ = run(capsys, "equations", EX / "grammars" / "pr5_variant9.cfg", "--max-len", "12")
    assert code == 0 and "S = {a}A{cc}" in out
    data = json.loads(run(capsys, "equations", EX / "grammars" / "anbn.cfg", "--json")[1])
    assert data["equal"] is True


def test_pump_explore_and_split(capsys):
    code, out, _ = run(capsys, "pump", "a e^{2n} b^n d^n c^{2n}", "--k", "4", "--n", "4")
    assert code == 0 and "не виконується" in out
    code, out, _ = run(capsys, "pump", "a^n b^n", "--k", "3", "--n", "2", "--split", "1,1,0,1")
    assert code == 0 and "a[a][b]b" in out


def test_sipl_commands(capsys):
    assert run(capsys, "sipl-check", EX / "sipl" / "valid" / "power.sipl")[0] == 0
    code, _, err = run(capsys, "sipl-check", EX / "sipl" / "invalid" / "missing_semicolon.sipl")
    assert code == 1 and "рядок 3" in err
    assert json.loads(run(capsys, "sipl-tree", EX / "sipl" / "valid" / "max.sipl", "--format", "json")[1])
    assert "digraph" in run(capsys, "sipl-tree", EX / "sipl" / "valid" / "max.sipl", "--format", "dot")[1]


@pytest.mark.parametrize(
    "args",
    [
        ["cnf", "no_such_file.cfg"],
        ["pump", "a^{2m}", "--k", "3"],
        ["pump", "a^n b^n", "--k", "3", "--split", "1,1"],
    ],
)
def test_bad_input_gives_exit_code_1(capsys, args):
    code, _, err = run(capsys, *args)
    assert code == 1 and err.startswith("помилка:")


def test_bad_grammar_from_stdin(capsys, monkeypatch):
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO("aS -> a"))
    code, _, err = run(capsys, "cnf", "-")
    assert code == 1 and "рядок 1" in err
