import json

import pandas as pd

from bloomberg_cli import bql_cli


class FakeBlp:
    def __init__(self):
        self.calls = []

    def bql(self, query, backend):
        self.calls.append((query, backend))
        return pd.DataFrame([{"ticker": "A Corp", "maturity": "2027-01-01"}])


def test_inline_query_makes_one_bql_call(monkeypatch, capsys):
    fake = FakeBlp()
    monkeypatch.setattr(bql_cli, "_blp", lambda: fake)
    query = "get(name, maturity) for(bonds('AAPL US Equity'))"
    assert bql_cli.run([query]) == 0
    assert fake.calls == [(query, "pandas")]
    assert json.loads(capsys.readouterr().out)[0]["ticker"] == "A Corp"


def test_file_query_makes_one_bql_call(monkeypatch, tmp_path):
    fake = FakeBlp()
    monkeypatch.setattr(bql_cli, "_blp", lambda: fake)
    query_file = tmp_path / "query.bql"
    query_file.write_text("get(count(group(id))) for(bonds('AAPL US Equity'))\n", encoding="utf-8")
    assert bql_cli.run(["--file", str(query_file)]) == 0
    assert fake.calls == [("get(count(group(id))) for(bonds('AAPL US Equity'))", "pandas")]


def test_rejects_query_and_file_without_bloomberg_call(monkeypatch, tmp_path, capsys):
    fake = FakeBlp()
    monkeypatch.setattr(bql_cli, "_blp", lambda: fake)
    query_file = tmp_path / "query.bql"
    query_file.write_text("get(px_last) for('AAPL US Equity')", encoding="utf-8")
    assert bql_cli.run(["get(px_last) for('IBM US Equity')", "--file", str(query_file)]) == 1
    assert fake.calls == []
    assert json.loads(capsys.readouterr().err)["type"] == "ValueError"
