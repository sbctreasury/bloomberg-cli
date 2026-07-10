import json

import pandas as pd

from bloomberg_cli import cli
from bloomberg_cli import surface


def test_frame_records_converts_dataframe():
    frame = pd.DataFrame([{"ticker": "AAPL US Equity", "field": "PX_LAST", "value": 123.45}])
    assert cli.frame_records(frame) == [
        {"ticker": "AAPL US Equity", "field": "PX_LAST", "value": 123.45}
    ]


def test_price_json(monkeypatch, capsys):
    monkeypatch.setattr(
        cli,
        "price",
        lambda security, field: {
            "security": security,
            "field": field,
            "value": 123.45,
            "elapsed_ms": 1.0,
        },
    )
    assert cli.run(["price", "AAPL US Equity"]) == 0
    assert json.loads(capsys.readouterr().out)["value"] == 123.45


def test_errors_are_structured(monkeypatch, capsys):
    def fail(*_args):
        raise RuntimeError("not connected")

    monkeypatch.setattr(cli, "price", fail)
    assert cli.run(["price", "AAPL US Equity"]) == 1
    error = json.loads(capsys.readouterr().err)
    assert error == {
        "error": "not connected",
        "type": "RuntimeError",
        "command": "price",
    }


def test_generic_call(monkeypatch, capsys):
    monkeypatch.setattr(cli, "invoke", lambda name, args, kwargs: {"name": name, "args": args, "kwargs": kwargs})
    assert cli.run(["call", "bdp", "--args", '["AAPL US Equity", "PX_LAST"]']) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["name"] == "bdp"
    assert result["args"] == ["AAPL US Equity", "PX_LAST"]


def test_generic_call_repeatable_arguments(monkeypatch, capsys):
    monkeypatch.setattr(cli, "invoke", lambda name, args, kwargs: {"name": name, "args": args, "kwargs": kwargs})
    assert cli.run([
        "call", "bdp", "--arg", "AAPL US Equity", "--arg", "PX_LAST", "--kw", "backend=pandas"
    ]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["args"] == ["AAPL US Equity", "PX_LAST"]
    assert result["kwargs"] == {"backend": "pandas"}


def test_catalog_includes_core_and_extensions():
    names = {row["name"] for row in surface.catalog()}
    assert "bdp" in names
    assert "ext.bond_info" in names
    assert "markets.market_info" in names
